import psycopg2
import logging
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Optional, List, Tuple, Any
from config import DB_CONFIG

log = logging.getLogger(__name__)


# DATABASE CONNECTION — Singleton

class Database:
    """Singleton для управления подключением к PostgreSQL."""
    _instance: Optional['Database'] = None

    def __new__(cls) -> 'Database':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @contextmanager
    def get_connection(self):
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init(self):
        """Создаёт все таблицы при старте."""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            conn.autocommit = True
            cur = conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id          SERIAL PRIMARY KEY,
                    brand       TEXT,
                    category    TEXT,
                    price       INTEGER,
                    material    TEXT,
                    color       TEXT,
                    city        TEXT,
                    wa_link     TEXT,
                    description TEXT,
                    seller_name TEXT,
                    photo_url   TEXT,
                    sizes       TEXT,
                    partner_id  INTEGER,
                    created_at  TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS photo_url TEXT")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS sizes TEXT")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS partner_id INTEGER")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS logs_general (
                    id             SERIAL PRIMARY KEY,
                    user_id        BIGINT,
                    city           TEXT,
                    requested_size TEXT,
                    query_text     TEXT,
                    action_type    TEXT,
                    seller_name    TEXT,
                    timestamp      TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS logs_search_requests (
                    id             SERIAL PRIMARY KEY,
                    user_id        BIGINT,
                    query_text     TEXT,
                    requested_size TEXT,
                    timestamp      TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reviews_service (
                    id          SERIAL PRIMARY KEY,
                    user_id     BIGINT,
                    review_text TEXT,
                    timestamp   TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reviews_product (
                    id          SERIAL PRIMARY KEY,
                    user_id     BIGINT,
                    review_text TEXT,
                    timestamp   TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id    BIGINT PRIMARY KEY,
                    username   TEXT,
                    first_name TEXT,
                    last_seen  TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS partners (
                    id           SERIAL PRIMARY KEY,
                    name         TEXT NOT NULL,
                    contact_info TEXT,
                    is_active    BOOLEAN DEFAULT TRUE,
                    created_at   TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS partner_stocks (
                    id         SERIAL PRIMARY KEY,
                    partner_id INTEGER REFERENCES partners(id) ON DELETE CASCADE,
                    item_id    INTEGER REFERENCES items(id) ON DELETE CASCADE,
                    quantity   INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS waiting_list (
                    id        SERIAL PRIMARY KEY,
                    user_id   BIGINT,
                    category  TEXT,
                    size      TEXT,
                    city      TEXT,
                    brand     TEXT,
                    timestamp TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.close()
            conn.close()
            log.info("Database.init: все таблицы созданы/проверены")
        except Exception as e:
            log.error(f"Database.init ОШИБКА: {e}")
            raise


# BASE REPOSITORY — абстрактный базовый класс

class BaseRepository(ABC):
    """Абстрактный репозиторий. Все репозитории наследуют db и _execute."""

    def __init__(self, db: Database):
        self.db = db

    def _execute(self, query: str, params: tuple = (), fetch: str = None) -> Any:
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if fetch == 'one':
                    return cur.fetchone()
                if fetch == 'all':
                    return cur.fetchall()
                return None

    def _execute_returning(self, query: str, params: tuple = ()) -> Any:
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchone()


# USER REPOSITORY

class UserRepository(BaseRepository):

    def save(self, user_id: int, username: str = None, first_name: str = None):
        try:
            self._execute("""
                INSERT INTO users (user_id, username, first_name, last_seen)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (user_id) DO UPDATE
                SET last_seen  = NOW(),
                    username   = EXCLUDED.username,
                    first_name = EXCLUDED.first_name
            """, (user_id, username, first_name))
        except Exception as e:
            log.error(f"UserRepository.save: {e}")

    def get_all_ids(self) -> List[int]:
        try:
            rows = self._execute(
                "SELECT user_id FROM users ORDER BY last_seen DESC", fetch='all')
            return [r[0] for r in rows] if rows else []
        except Exception as e:
            log.error(f"UserRepository.get_all_ids: {e}")
            return []

    def count(self) -> int:
        try:
            row = self._execute("SELECT COUNT(*) FROM users", fetch='one')
            return row[0] if row else 0
        except Exception:
            return 0


# ITEM REPOSITORY

class ItemRepository(BaseRepository):

    def add(self, brand: str, category: str, price: int, material: str,
            color: str, city: str, wa_link: str, description: str,
            seller_name: str, photo_url: str = None, sizes: str = None,
            partner_id: int = None) -> Optional[int]:
        row = self._execute_returning("""
            INSERT INTO items
                (brand, category, price, material, color, city,
                 wa_link, description, seller_name, photo_url, sizes, partner_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (brand, category, int(price), material, color, city,
              wa_link, description, seller_name, photo_url, sizes, partner_id))
        return row[0] if row else None

    def get_by_id(self, item_id: int) -> Optional[Tuple]:
        return self._execute("""
            SELECT id, brand, category, price, material, color, city,
                   wa_link, description, seller_name, photo_url, sizes, partner_id
            FROM items WHERE id = %s
        """, (item_id,), fetch='one')

    def get_all(self) -> List[Tuple]:
        return self._execute("""
            SELECT id, brand, category, price, city, photo_url, sizes, partner_id
            FROM items ORDER BY created_at DESC
        """, fetch='all') or []

    def update_field(self, item_id: int, field: str, value: Any):
        allowed = {'brand', 'category', 'price', 'material', 'color',
                   'city', 'wa_link', 'description', 'seller_name',
                   'photo_url', 'sizes', 'partner_id'}
        if field not in allowed:
            raise ValueError(f"Недопустимое поле: {field}")
        self._execute(
            f"UPDATE items SET {field} = %s WHERE id = %s", (value, item_id))

    def delete(self, item_id: int):
        self._execute("DELETE FROM items WHERE id = %s", (item_id,))

    def get_unique_cities(self) -> List[str]:
        rows = self._execute("""
            SELECT DISTINCT city FROM items
            WHERE city IS NOT NULL ORDER BY city
        """, fetch='all')
        return [r[0] for r in rows] if rows else []

    def get_unique_brands(self, city: str) -> List[str]:
        rows = self._execute("""
            SELECT DISTINCT brand FROM items
            WHERE LOWER(city) = LOWER(%s) AND brand IS NOT NULL ORDER BY brand
        """, (city,), fetch='all')
        return [r[0] for r in rows] if rows else []

    def get_unique_categories(self, city: str, brand: str) -> List[str]:
        rows = self._execute("""
            SELECT DISTINCT category FROM items
            WHERE LOWER(city) = LOWER(%s)
              AND LOWER(brand) = LOWER(%s)
              AND category IS NOT NULL ORDER BY category
        """, (city, brand), fetch='all')
        return [r[0] for r in rows] if rows else []

    def search(self, brand: str, category: str, city: str,
               price: int, size: str = None) -> List[Tuple]:
        if size:
            return self._execute("""
                SELECT id, brand, category, price, wa_link, seller_name,
                       material, color, city, description, photo_url, sizes, partner_id
                FROM items
                WHERE LOWER(brand)    = LOWER(%s)
                  AND LOWER(category) = LOWER(%s)
                  AND LOWER(city)     = LOWER(%s)
                  AND price <= %s
                  AND (sizes IS NULL OR sizes = '' OR sizes ILIKE %s)
                ORDER BY price ASC
            """, (brand, category, city, price, f'%{size}%'), fetch='all') or []
        return self._execute("""
            SELECT id, brand, category, price, wa_link, seller_name,
                   material, color, city, description, photo_url, sizes, partner_id
            FROM items
            WHERE LOWER(brand)    = LOWER(%s)
              AND LOWER(category) = LOWER(%s)
              AND LOWER(city)     = LOWER(%s)
              AND price <= %s
            ORDER BY price ASC
        """, (brand, category, city, price), fetch='all') or []

    def search_similar(self, category: str, city: str) -> List[Tuple]:
        try:
            return self._execute("""
                SELECT id, brand, category, price, wa_link, seller_name,
                       material, color, city, description, photo_url, sizes, partner_id
                FROM items
                WHERE LOWER(city)     = LOWER(%s)
                  AND LOWER(category) = LOWER(%s)
                ORDER BY price ASC LIMIT 1
            """, (city, category), fetch='all') or []
        except Exception as e:
            log.error(f"ItemRepository.search_similar: {e}")
            return []


# LOG REPOSITORY

class LogRepository(BaseRepository):

    def log_action(self, user_id: int, city: str, size: str,
                   query: str, action: str, seller: str = None):
        try:
            self._execute("""
                INSERT INTO logs_general
                    (user_id, city, requested_size, query_text, action_type, seller_name)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (user_id, city, size, query, action, seller))
        except Exception as e:
            log.error(f"LogRepository.log_action: {e}")

    def log_search_fail(self, user_id: int, query: str, size: str):
        try:
            self._execute("""
                INSERT INTO logs_search_requests (user_id, query_text, requested_size)
                VALUES (%s,%s,%s)
            """, (user_id, query, size))
        except Exception as e:
            log.error(f"LogRepository.log_search_fail: {e}")

    def save_review_service(self, user_id: int, text: str):
        try:
            self._execute(
                "INSERT INTO reviews_service (user_id, review_text) VALUES (%s,%s)",
                (user_id, text))
        except Exception as e:
            log.error(f"LogRepository.save_review_service: {e}")

    def save_review_product(self, user_id: int, text: str):
        try:
            self._execute(
                "INSERT INTO reviews_product (user_id, review_text) VALUES (%s,%s)",
                (user_id, text))
        except Exception as e:
            log.error(f"LogRepository.save_review_product: {e}")

    def get_action_counts(self) -> List[Tuple]:
        return self._execute("""
            SELECT action_type, COUNT(*) AS cnt
            FROM logs_general GROUP BY action_type ORDER BY cnt DESC
        """, fetch='all') or []

    def get_search_fails_count(self) -> int:
        row = self._execute("SELECT COUNT(*) FROM logs_search_requests", fetch='one')
        return row[0] if row else 0

    def get_recent_service_reviews(self, limit: int = 50) -> List[Tuple]:
        return self._execute("""
            SELECT user_id, review_text, timestamp
            FROM reviews_service ORDER BY timestamp DESC LIMIT %s
        """, (limit,), fetch='all') or []

    def get_recent_product_reviews(self, limit: int = 50) -> List[Tuple]:
        return self._execute("""
            SELECT user_id, review_text, timestamp
            FROM reviews_product ORDER BY timestamp DESC LIMIT %s
        """, (limit,), fetch='all') or []

    def get_full_stats(self) -> dict:
        stats = {}
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM users")
                    stats['users'] = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM logs_general WHERE action_type = 'Описание выдано'")
                    stats['searches'] = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM logs_general WHERE action_type = 'Перешел на ватсап'")
                    stats['wa_clicks'] = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM logs_search_requests")
                    stats['fails'] = cur.fetchone()[0]
                    cur.execute("""
                        SELECT query_text, COUNT(*) as cnt FROM logs_general
                        WHERE action_type = 'Описание выдано'
                        GROUP BY query_text ORDER BY cnt DESC LIMIT 5
                    """)
                    stats['top_queries'] = cur.fetchall()
                    cur.execute("SELECT COUNT(*) FROM reviews_service")
                    stats['reviews_service'] = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM reviews_product")
                    stats['reviews_product'] = cur.fetchone()[0]
        except Exception as e:
            log.error(f"LogRepository.get_full_stats: {e}")
        return stats

    def get_traffic_for_export(self) -> List[Tuple]:
        return self._execute("""
            SELECT u.user_id, COALESCE(u.username,'—'), COALESCE(u.first_name,'—'),
                   g.query_text, g.city, g.requested_size, g.action_type, g.timestamp
            FROM logs_general g
            LEFT JOIN users u ON g.user_id = u.user_id
            ORDER BY g.timestamp DESC
        """, fetch='all') or []

    def get_sales_for_export(self) -> List[Tuple]:
        return self._execute("""
            SELECT u.user_id, COALESCE(u.username,'—'), COALESCE(u.first_name,'—'),
                   g.query_text, g.city, g.requested_size, g.seller_name,
                   COALESCE(p.name,'—'), COALESCE(p.contact_info,'—'), g.timestamp
            FROM logs_general g
            LEFT JOIN users u ON g.user_id = u.user_id
            LEFT JOIN items i ON g.seller_name = i.seller_name
            LEFT JOIN partners p ON i.partner_id = p.id
            WHERE g.action_type IN ('Перешел на ватсап','whatsapp_redirect')
            ORDER BY g.timestamp DESC
        """, fetch='all') or []


# PARTNER REPOSITORY

class PartnerRepository(BaseRepository):

    def add(self, name: str, contact_info: str = None) -> Optional[int]:
        try:
            row = self._execute_returning(
                "INSERT INTO partners (name, contact_info) VALUES (%s,%s) RETURNING id",
                (name, contact_info))
            return row[0] if row else None
        except Exception as e:
            log.error(f"PartnerRepository.add: {e}")
            return None

    def get_by_id(self, partner_id: int) -> Optional[Tuple]:
        return self._execute(
            "SELECT id, name, contact_info, is_active FROM partners WHERE id = %s",
            (partner_id,), fetch='one')

    def get_all(self, only_active: bool = True) -> List[Tuple]:
        if only_active:
            return self._execute(
                "SELECT id, name, contact_info, is_active FROM partners WHERE is_active = TRUE ORDER BY id",
                fetch='all') or []
        return self._execute(
            "SELECT id, name, contact_info, is_active FROM partners ORDER BY id",
            fetch='all') or []

    def set_active(self, partner_id: int, is_active: bool):
        self._execute(
            "UPDATE partners SET is_active = %s WHERE id = %s",
            (is_active, partner_id))

    def get_items(self, partner_id: int) -> List[Tuple]:
        return self._execute("""
            SELECT id, brand, category, price, city, sizes, photo_url
            FROM items WHERE partner_id = %s ORDER BY created_at DESC
        """, (partner_id,), fetch='all') or []

    def get_stats(self, partner_id: int) -> dict:
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM items WHERE partner_id = %s", (partner_id,))
                    items_count = cur.fetchone()[0]
                    cur.execute("""
                        SELECT COUNT(*) FROM logs_general g
                        JOIN items i ON g.seller_name = i.seller_name
                        WHERE i.partner_id = %s AND g.action_type = 'Описание выдано'
                    """, (partner_id,))
                    views = cur.fetchone()[0]
                    cur.execute("""
                        SELECT COUNT(*) FROM logs_general g
                        JOIN items i ON g.seller_name = i.seller_name
                        WHERE i.partner_id = %s
                          AND g.action_type IN ('Перешел на ватсап','whatsapp_redirect')
                    """, (partner_id,))
                    wa_clicks = cur.fetchone()[0]
            return {'items': items_count, 'views': views, 'wa_clicks': wa_clicks}
        except Exception as e:
            log.error(f"PartnerRepository.get_stats: {e}")
            return {'items': 0, 'views': 0, 'wa_clicks': 0}

    def set_stock(self, partner_id: int, item_id: int, quantity: int):
        self._execute("""
            INSERT INTO partner_stocks (partner_id, item_id, quantity, updated_at)
            VALUES (%s,%s,%s,NOW())
            ON CONFLICT (partner_id, item_id) DO UPDATE
            SET quantity = EXCLUDED.quantity, updated_at = NOW()
        """, (partner_id, item_id, quantity))


# WAITING LIST REPOSITORY

class WaitingListRepository(BaseRepository):

    def add(self, user_id: int, category: str, size: str,
            city: str, brand: str = None):
        try:
            self._execute("""
                INSERT INTO waiting_list (user_id, category, size, city, brand)
                VALUES (%s,%s,%s,%s,%s)
            """, (user_id, category, size, city, brand))
        except Exception as e:
            log.error(f"WaitingListRepository.add: {e}")

    def get_matching_users(self, category: str, city: str,
                           sizes: str = None) -> List[int]:
        try:
            rows = self._execute("""
                SELECT DISTINCT user_id, size FROM waiting_list
                WHERE LOWER(category) = LOWER(%s) AND LOWER(city) = LOWER(%s)
            """, (category, city), fetch='all') or []
            if not rows or not sizes:
                return [r[0] for r in rows]
            size_list = [s.strip() for s in sizes.split(';')]
            return [uid for uid, usize in rows if usize in size_list]
        except Exception as e:
            log.error(f"WaitingListRepository.get_matching_users: {e}")
            return []

    def remove(self, user_id: int, category: str, city: str):
        try:
            self._execute("""
                DELETE FROM waiting_list
                WHERE user_id = %s
                  AND LOWER(category) = LOWER(%s)
                  AND LOWER(city) = LOWER(%s)
            """, (user_id, category, city))
        except Exception as e:
            log.error(f"WaitingListRepository.remove: {e}")


# FACADE — единая точка доступа

class Repository:
    """Фасад над всеми репозиториями. repo = Repository()"""

    def __init__(self):
        self._db      = Database()
        self.users    = UserRepository(self._db)
        self.items    = ItemRepository(self._db)
        self.logs     = LogRepository(self._db)
        self.partners = PartnerRepository(self._db)
        self.waiting  = WaitingListRepository(self._db)

    def init_db(self):
        self._db.init()

    def get_connection(self):
        return psycopg2.connect(**DB_CONFIG)


# Глобальный экземпляр
repo = Repository()


# LEGACY SHIMS — совместимость с main.py без изменений

def get_connection():                            return repo.get_connection()
def init_db():                                   repo.init_db()
def save_user(uid, username=None, fn=None):      repo.users.save(uid, username, fn)
def get_all_user_ids():                          return repo.users.get_all_ids()
def get_users_count():                           return repo.users.count()
def get_unique_cities():                         return repo.items.get_unique_cities()
def get_unique_brands(city):                     return repo.items.get_unique_brands(city)
def get_unique_categories(city, brand):          return repo.items.get_unique_categories(city, brand)
def search_items_v4(b, c, ci, p, size=None):     return repo.items.search(b, c, ci, p, size)
def search_similar(cat, city):                   return repo.items.search_similar(cat, city)
def add_item(**kw):                              return repo.items.add(**kw)
def get_all_items():                             return repo.items.get_all()
def get_item_by_id(iid):                         return repo.items.get_by_id(iid)
def update_item_field(iid, f, v):                repo.items.update_field(iid, f, v)
def delete_item(iid):                            repo.items.delete(iid)
def log_action(uid, city, sz, q, act, seller=None): repo.logs.log_action(uid, city, sz, q, act, seller)
def log_search_fail(uid, q, sz):                 repo.logs.log_search_fail(uid, q, sz)
def save_review_service(uid, txt):               repo.logs.save_review_service(uid, txt)
def save_review_product(uid, txt):               repo.logs.save_review_product(uid, txt)
def get_logs_stats():                            return repo.logs.get_action_counts()
def get_search_fails_count():                    return repo.logs.get_search_fails_count()
def get_recent_reviews_service(n=50):            return repo.logs.get_recent_service_reviews(n)
def get_recent_reviews_product(n=50):            return repo.logs.get_recent_product_reviews(n)
def get_full_stats():                            return repo.logs.get_full_stats()
def get_all_partners(only_active=True):          return repo.partners.get_all(only_active)
def get_partner_by_id(pid):                      return repo.partners.get_by_id(pid)
def add_partner(name, contact=None):             return repo.partners.add(name, contact)
def set_partner_active(pid, active):             repo.partners.set_active(pid, active)
def get_partner_items(pid):                      return repo.partners.get_items(pid)
def get_partner_stats(pid):                      return repo.partners.get_stats(pid)
def set_partner_stock(pid, iid, qty):            repo.partners.set_stock(pid, iid, qty)
def add_to_waiting_list(uid, cat, sz, city, b=None): repo.waiting.add(uid, cat, sz, city, b)
def get_waiting_users(cat, city, sizes=None):    return repo.waiting.get_matching_users(cat, city, sizes)
def remove_from_waiting_list(uid, cat, city):    repo.waiting.remove(uid, cat, city)
