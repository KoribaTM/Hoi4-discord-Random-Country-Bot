import disnake
from disnake.ext import commands
import random
import json
import os
from dotenv import load_dotenv
from typing import Dict, Any
import logging

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MY_SERVER_ID = int(os.getenv("SERVER_ID", 1493738822918475846))

IDEOLOGIES = ["Коммунизм", "Демократия", "Фашизм", "Нейтралитет"]
IDEOLOGY_COLORS = {
    "Коммунизм": 0xff0000,   # red
    "Демократия": 0x0000ff,   # blue
    "Фашизм": 0x8b4513,      # brown
    "Нейтралитет": 0x808080  # gray
}
DIFFICULTY_NAMES = {
    "easy": "🟢 Лёгкая (Мажоры)",
    "normal": "🟡 Средняя (Регионалы)",
    "hard": "🔴 Сложная (Миноры/Сложные)"
}

class CountryManager:
    def __init__(self, data_file='countries.json'):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_file = os.path.join(base_dir, data_file)
        self.data = self.load_data()
        logger.info(f"Загружено {self.total_countries()} стран")
        logger.info(f"Файл загружен из: {self.data_file}")
    
    def load_data(self) -> Dict[str, Dict]:
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Файл {self.data_file} не найден!")
            return {"easy": {}, "normal": {}, "hard": {}}
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            return {"easy": {}, "normal": {}, "hard": {}}
    
    def get_country_pool(self, difficulty: str) -> Dict[str, Any]:
        return self.data.get(difficulty, {})
    
    def get_random_country(self, difficulty: str):
        pool = self.get_country_pool(difficulty)
        if not pool:
            return None, None
        
        name = random.choice(list(pool.keys()))
        return name, pool[name]
    
    def total_countries(self) -> int:
        return sum(len(pool) for pool in self.data.values())
    
    def count_by_difficulty(self, difficulty: str) -> int:
        return len(self.data.get(difficulty, {}))
    
country_manager = CountryManager()

intents = disnake.Intents.default()
intents.message_content = True  # Если нужно читать сообщения
bot = commands.InteractionBot(test_guilds=[MY_SERVER_ID])

@bot.event
async def on_ready():
    logger.info(f"✅ Бот {bot.user} успешно запущен!")
    logger.info(f"📡 Подключен к серверу ID: {MY_SERVER_ID}")
    logger.info(f"📊 Загружено стран: {country_manager.total_countries()}")

@bot.slash_command(
    name="country",
    description="🎲 Случайно выбирает страну и идеологию для игры в Hearts of Iron IV"
)
async def country(
    inter: disnake.ApplicationCommandInteraction,
    difficulty: str = commands.Param(
        name="сложность",
        description="Выберите уровень сложности игры",
        choices=[
            disnake.OptionChoice(name="🟢 Легко (Мажоры)", value="easy"),
            disnake.OptionChoice(name="🟡 Нормально (Регионалы)", value="normal"),
            disnake.OptionChoice(name="🔴 Сложно (Миноры/Сложные)", value="hard"),
        ]
    )
):
    await inter.response.defer()

    country_name, country_info = country_manager.get_random_country(difficulty)
    
    if not country_name:
        await inter.edit_original_response(
            content="Ошибка: нет стран для выбранной сложности!\n"
                   "Пожалуйста, обновите файл countries.json"
        )
        return
    
    selected_ideology = random.choice(IDEOLOGIES)
    tag = country_info.get("tag", "???")
    color = IDEOLOGY_COLORS[selected_ideology]

    embed = disnake.Embed(
        title="🎖️ Ваша судьба в Hearts of Iron IV",
        description=f"Вам выпала страна для игры!",
        color=color
    )
    
    embed.add_field(
        name="🎲 Сложность",
        value=f"**{DIFFICULTY_NAMES[difficulty]}**",
        inline=False
    )
    
    embed.add_field(
        name="🌍 Государство",
        value=f"**{country_name}**\n*Тег: `{tag}`*",
        inline=True
    )
    
    embed.add_field(
        name="📜 Идеология",
        value=f"**{selected_ideology}**",
        inline=True
    )
    
    if "default_ideology" in country_info:
        embed.add_field(
            name="📌 Стандартная идеология",
            value=f"*{country_info['default_ideology']}*",
            inline=False
        )
    
    embed.set_footer(
        text="Hearts of Iron IV | Удачи, командующий! 🎮",
        icon_url="https://cdn.discordapp.com/..." # Опционально: иконка
    )
    
    await inter.edit_original_response(embed=embed)

@bot.slash_command(
    name="stats",
    description="📊 Показывает статистику по странам в базе данных"
)
async def stats(inter: disnake.ApplicationCommandInteraction):
    """Команда для просмотра статистики"""
    
    embed = disnake.Embed(
        title="📊 Статистика стран HoI4",
        description="Количество доступных стран по уровням сложности",
        color=0x00ff00
    )
    
    for difficulty, name in DIFFICULTY_NAMES.items():
        count = country_manager.count_by_difficulty(difficulty)
        embed.add_field(
            name=name,
            value=f"**{count}** стран",
            inline=True
        )
    
    embed.add_field(
        name="📌 Всего",
        value=f"**{country_manager.total_countries()}** стран в базе",
        inline=False
    )
    
    embed.set_footer(text="Данные из countries.json")
    
    await inter.response.send_message(embed=embed)

@bot.slash_command(
    name="random_country",
    description="🎲 Получить случайную страну без выбора сложности"
)
async def random_country(
    inter: disnake.ApplicationCommandInteraction,
    exclude_ideology: str = commands.Param(
        name="исключить_идеологию",
        description="Исключить определенную идеологию",
        choices=[
            disnake.OptionChoice(name="Коммунизм", value="Коммунизм"),
            disnake.OptionChoice(name="Демократия", value="Демократия"),
            disnake.OptionChoice(name="Фашизм", value="Фашизм"),
            disnake.OptionChoice(name="Нейтралитет", value="Нейтралитет"),
            disnake.OptionChoice(name="Не исключать", value="none"),
        ],
        default="none"
    )
):
    
    await inter.response.defer()
    
    all_countries = {}
    for difficulty in country_manager.data:
        all_countries.update(country_manager.data[difficulty])
    
    if not all_countries:
        await inter.edit_original_response(content="❌ Нет доступных стран!")
        return
    
    country_name = random.choice(list(all_countries.keys()))
    country_info = all_countries[country_name]
    
    if exclude_ideology == "none":
        selected_ideology = random.choice(IDEOLOGIES)
    else:
        available_ideologies = [ideology for ideology in IDEOLOGIES if ideology != exclude_ideology]
        if not available_ideologies:
            await inter.edit_original_response(
                content=f"❌ Нет доступных идеологий для выбора после исключения {exclude_ideology}!"
            )
            return
        selected_ideology = random.choice(available_ideologies)
    
    embed = disnake.Embed(
        title="🎲 Случайная страна",
        color=IDEOLOGY_COLORS[selected_ideology]
    )
    embed.add_field(
        name="🌍 Страна",
        value=f"**{country_name}**\n*Тег: `{country_info.get('tag', '???')}`*",
        inline=True
    )
    embed.add_field(
        name="📜 Идеология",
        value=f"**{selected_ideology}**",
        inline=True
    )
    
    if exclude_ideology != "none":
        embed.add_field(
            name="🚫 Исключенная идеология",
            value=f"*{exclude_ideology}*",
            inline=False
        )
    
    await inter.edit_original_response(embed=embed)



@bot.event
async def on_command_error(inter: disnake.ApplicationCommandInteraction, error):
    """Глобальный обработчик ошибок"""
    if isinstance(error, disnake.errors.Forbidden):
        await inter.response.send_message(
            "У меня нет прав для выполнения этой команды!",
            ephemeral=True
        )
    else:
        logger.error(f"Ошибка: {error}")
        await inter.response.send_message(
            "Произошла ошибка при выполнении команды!",
            ephemeral=True
        )


if __name__ == "__main__":
    if not TOKEN:
        logger.error("Ошибка: TOKEN не найден в переменных окружения")
        exit(1)
    
    try:
        bot.run(TOKEN)
    except disnake.errors.LoginFailure:
        logger.error("Неверный токен.")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")