import asyncio
import logging
import random
from datetime import datetime
import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import config
import database
from solver import InstaLingSolver
from firebase_sync import FirebaseClient

logger = logging.getLogger("InstaLingBot.Scheduler")

class SessionScheduler:
    def __init__(self, bot: discord.Client, solver: InstaLingSolver, firebase: FirebaseClient):
        self.bot = bot
        self.solver = solver
        self.firebase = firebase
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Uruchamia harmonogram sesji w godzinach 16:00 - 23:00 codziennie"""
        cron_hours = getattr(config, "AUTO_CRON_HOURS", "16,18,20,22")
        cron_minute = getattr(config, "AUTO_CRON_MINUTE", 30)

        self.scheduler.add_job(
            self.run_daily_sessions,
            CronTrigger(hour=cron_hours, minute=cron_minute),
            id="daily_instaling_job",
            replace_existing=True
        )
        self.scheduler.start()
        logger.info(f"⏰ Harmonogram aktywny! Sesje w godzinach 16:00 - 23:00 (sprawdzanie: {cron_hours}, min: {cron_minute:02d}).")

    async def run_daily_sessions(self):
        """Wykonuje sesje dla kont w godzinach 16:00 - 23:00, pomijając te już ukończone dzisiaj"""
        now = datetime.now()
        start_hour = getattr(config, "AUTO_WINDOW_START_HOUR", 16)
        end_hour = getattr(config, "AUTO_WINDOW_END_HOUR", 23)

        # Upewnij się, że mieścimy się w zadanym oknie czasowym 16:00 - 23:00
        if not (start_hour <= now.hour <= end_hour):
            logger.info(f"⏳ Poza oknem aktywności sesji ({start_hour}:00 - {end_hour}:00). Pomijam auto-sesje.")
            return

        logger.info(f"🌅 [AUTO-SESJE] Rozpoczynam sprawdzanie kont w oknie {start_hour}:00 - {end_hour}:00...")
        accounts = database.get_all_auto_accounts()
        if not accounts:
            logger.info("Brak aktywnych kont z włączonym harmonogramem.")
            return

        # Filtruj konta: wykonaj tylko te, które NIE zostały dzisiaj pomyślnie zrobione
        pending_accounts = []
        for acc in accounts:
            if database.is_session_done_today(acc):
                logger.info(f"⏩ Konto `{acc['login']}` ma już ukończoną sesję na dziś ({acc.get('last_run')}). Pomijam.")
            else:
                pending_accounts.append(acc)

        if not pending_accounts:
            logger.info("🎉 Wszystkie zarejestrowane konta mają już zrobioną dzisiejszą sesję! Brak zaległości.")
            return

        # Zaktualizuj bazę Firebase przed rozpoczęciem
        await self.firebase.fetch_database()

        remaining_accounts = list(pending_accounts)
        batch_idx = 1
        total_accounts = len(pending_accounts)
        processed_count = 0

        logger.info(f"📋 Rozpoczynam wykonywanie sesji dla {total_accounts} kont do zrobienia...")

        while remaining_accounts:
            batch_size = random.randint(config.BATCH_SIZE_MIN, config.BATCH_SIZE_MAX)
            current_batch = remaining_accounts[:batch_size]
            remaining_accounts = remaining_accounts[batch_size:]

            logins_str = ", ".join([a['login'] for a in current_batch])
            logger.info(f"📦 Paczka #{batch_idx} ({len(current_batch)} kont: {logins_str}). Postęp: {processed_count}/{total_accounts}...")

            async def solve_and_notify(acc, index_in_batch):
                await asyncio.sleep(index_in_batch * random.uniform(8.0, 15.0))
                user_id = acc["discord_user_id"]
                login = acc["login"]
                password = acc["password"]
                lang = acc.get("language", "auto")

                logger.info(f"⚙️ Auto-sesja dla konta: {login} ({lang.upper()})...")
                try:
                    res = await self.solver.solve_session(login, password, lang)

                    # Jeśli sesja nie powiodła się z powodu timeoutu/błędu sieci (ale nie błędnego hasła), spróbuj raz jeszcze
                    if not res["success"] and not res.get("already_done") and "niepoprawny login" not in res.get("message", "").lower():
                        logger.warning(f"⚠️ Pierwsza próba sesji dla {login} nie powiodła się ({res.get('message')}). Ponawiam próbę za 15s...")
                        await asyncio.sleep(random.uniform(12.0, 18.0))
                        res = await self.solver.solve_session(login, password, lang)

                    is_success = res.get("success", False)
                    is_already_done = res.get("already_done", False)
                    status_str = "already_done" if is_already_done else ("success" if is_success else "failed")
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # Zapisz wynik w bazie
                    database.update_last_run(user_id, login, now_str, status=status_str)
                    up_acc = database.get_account_by_login(user_id, login)
                    if up_acc:
                        asyncio.create_task(self.firebase.save_account_cloud(up_acc))

                    # Wyślij powiadomienie na PV (DM) do użytkownika
                    try:
                        user = await self.bot.fetch_user(user_id)
                        if user:
                            if is_success or is_already_done:
                                embed = discord.Embed(
                                    title="⏰ Automatyczna Sesja InstaLing",
                                    color=discord.Color.green(),
                                    timestamp=datetime.now()
                                )
                                embed.add_field(name="👤 Konto", value=f"`{login}`", inline=True)
                                embed.add_field(name="🎯 Język", value=f"`{res.get('language', 'PL')}`", inline=True)
                                embed.add_field(name="⏱️ Czas", value=f"`{res.get('time_seconds', 0)}s`", inline=True)

                                if is_already_done:
                                    embed.description = "ℹ️ Dzisiejsza sesja była już wcześniej wykonana."
                                else:
                                    embed.description = "✅ Twoja dzisiejsza sesja została pomyślnie wykonana!"
                                    embed.add_field(name="📊 Rozwiązane", value=f"`{res.get('correct_words', 0)}/{res.get('total_words', 0)}`", inline=True)
                                    embed.add_field(name="🧠 Nowe słówka", value=f"`+{res.get('learned_words', 0)}`", inline=True)

                                embed.set_footer(text="InstaLing AutoBot • dc.zinzelekk")
                                await user.send(embed=embed)
                            else:
                                # Szczegółowy raport błędu na PV ("czm się nie udało")
                                err_msg = res.get("message") or "Wystąpił błąd podczas sesji"
                                err_reason = res.get("error_reason") or "Błąd wykonania sesji"
                                err_tip = res.get("error_tip") or "Użyj komendy /sesja lub sprawdź dane logowania."
                                retry_info = "🔄 *Bot spróbuje ponownie w kolejnym oknie (między 16:00 a 23:00).*" if datetime.now().hour < 22 else "⚠️ *To była ostatnia próba w dzisiejszym oknie 16-23. Sprawdź konto ręcznie.*"

                                embed = discord.Embed(
                                    title=f"🚨 Błąd sesji InstaLing — Konto: `{login}`",
                                    description=(
                                        f"Automatyczna sesja dla Twojego konta **`{login}`** nie powiodła się.\n\n"
                                        f"**❌ Dlaczego się nie udało:**\n> {err_msg}\n\n"
                                        f"**⚠️ Rodzaj problemu:**\n> `{err_reason}`\n\n"
                                        f"**💡 Co możesz zrobić:**\n> {err_tip}\n\n"
                                        f"{retry_info}"
                                    ),
                                    color=discord.Color.red(),
                                    timestamp=datetime.now()
                                )
                                embed.add_field(name="👤 Login", value=f"`{login}`", inline=True)
                                embed.add_field(name="🎯 Język", value=f"`{res.get('language', 'PL')}`", inline=True)
                                embed.add_field(name="⏱️ Czas próby", value=f"`{res.get('time_seconds', 0)}s`", inline=True)
                                embed.set_footer(text="InstaLing AutoBot • Powiadomienie o błędzie")
                                await user.send(embed=embed)
                    except Exception as e_dm:
                        logger.warning(f"Nie udało się wysłać DM do {user_id}: {e_dm}")

                    return acc, res
                except Exception as e:
                    logger.error(f"Błąd auto-sesji dla {login}: {e}")
                    return acc, {
                        "success": False,
                        "message": str(e),
                        "error_reason": "Wyjątek systemowy",
                        "error_tip": "Wystąpił nieoczekiwany błąd w procesie bota.",
                        "total_words": 0,
                        "correct_words": 0,
                        "learned_words": 0
                    }

            batch_tasks = [solve_and_notify(acc, i) for i, acc in enumerate(current_batch)]
            await asyncio.gather(*batch_tasks)

            processed_count += len(current_batch)
            batch_idx += 1

            if remaining_accounts:
                pause_time = random.uniform(config.BATCH_PAUSE_MIN, config.BATCH_PAUSE_MAX)
                logger.info(f"☕ Paczka ukończona. Przerwa {pause_time:.1f}s przed kolejną paczką...")
                await asyncio.sleep(pause_time)

        logger.info(f"🎉 Zakończono turę sprawdzania sesji w oknie 16:00 - 23:00!")
