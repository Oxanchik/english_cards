#  Learn English by Cards — Telegram Bot 📚 ![logo_telegram](./images/telegram_logo.png)
Программа для управления ботом для изучения английского языка по карточкам слов.

Ссылка на бота: [@test_EnglishCardsBot](https://t.me/test_EnglishCardsBot)

## Программа
  1) 
  

## Инструкция по запуску проекта

**1. Установите Python**

Убедитесь, что у вас установлен Python 3.8+

```bash
python --version
```
Если Python не установлен: https://www.python.org/downloads/

**2. Клонируйте репозиторий:**
```bash
git clone git@github.com:Oxanchik/telegram_bot_english.git
cd clients_homework
```

**3. Создайте и активируйте виртуальное окружение (по желанию):**

Windows:
```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**4. Установите зависимости:**
```bash
pip install -r requirements.txt
```

**5. Настройте пароль к Postgres и токен своего телеграм-бота**

Скопируйте файл-пример и переименуйте его в .env
```bash
cp .env.example .env        # macOS/Linux
copy .env.example .env      # Windows
```

Откройте файл .env в любом текстовом редакторе и замените your_password_here на ваш пароль, 
и введите токен от вашего бота Telegram вместо your_telegram_bot_token_here:
```bash
PASS='your_password_here'
TOKEN='your_telegram_bot_token_here'
```
Также можно заменить логин и название базы данных:
```bash
LOGIN='postgres'
DBNAME='english_cards'
```

**6. Запустите программу:**
```bash
python main.py
```

## Пример работы
```text
Инициализация БД...
✅ База данных 'english_cards' создана

```

## Требования
- Python 3.8+ (проверено на 3.14)
- **Зависимости**: все необходимые библиотеки указаны в `requirements.txt`
