# Jarvis Shoe Bot 👟

Telegram-бот для поиска и продажи обуви с системой партнёров, листом ожидания и аналитикой.

## Технологии

- Python 3.10+
- pyTelegramBotAPI
- PostgreSQL (Supabase)
- APScheduler
- pandas + openpyxl

## Установка

### 1. Клонируй репозиторий
```bash
git clone https://github.com/твой_username/jarvis-shoe-bot.git
cd jarvis-shoe-bot
```

### 2. Установи зависимости
```bash
pip install -r requirements.txt
```

### 3. Настрой переменные окружения
```bash
cp .env.example .env
nano .env  # заполни своими данными
```

### 4. Создай таблицы в Supabase
Выполни SQL из файла `init.sql` в Supabase SQL Editor.

### 5. Запусти бота
```bash
python3 main.py
```

## Деплой на VPS (systemd)

```bash
cp jarvis.service /etc/systemd/system/
cp start_jarvis.sh /root/
chmod +x /root/start_jarvis.sh
systemctl daemon-reload
systemctl enable jarvis
systemctl start jarvis
```

## Команды бота

| Команда | Описание |
|---|---|
| `/start` | Начать поиск обуви |
| `/admin` | Панель администратора |
| `/partners` | Список партнёров |
| `/add_partner Название \| Контакт` | Добавить партнёра |
| `/deactivate_partner [id]` | Деактивировать партнёра |

## Архитектура

```
JarvisBot
├── ReviewHandler    — таймеры отзывов
├── ClientHandler    — поиск товара
├── AdminHandler     — управление, статистика, Excel
└── VendorHandler    — панель партнёра

Repository (Facade)
├── UserRepository
├── ItemRepository
├── LogRepository
├── PartnerRepository
└── WaitingListRepository
```

## Структура БД

- `items` — товары
- `users` — пользователи
- `partners` — партнёры
- `partner_stocks` — остатки у партнёров
- `waiting_list` — лист ожидания
- `logs_general` — действия пользователей
- `logs_search_requests` — неудачные поиски
- `reviews_service` — отзывы о сервисе
- `reviews_product` — отзывы о товарах
