import os
import json

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

load_dotenv()
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv("DB_PASS", 'postgres')
DB_NAME = os.getenv('DB_NAME', 'english_cards_db')


def get_db_connection(db_name="postgres"):
    """
    Установить соединение с базой данных PostgreSQL.

    Функция создаёт и возвращает соединение с PostgreSQL, используя параметры
    подключения из переменных окружения. По умолчанию подключается к системной
    базе данных 'postgres', но можно указать любую другую базу данных.

    Args:
    db_name (str): Имя базы данных для подключения.
    По умолчанию 'postgres' (системная БД)

    Returns:
    psycopg2.connection: Объект соединения с PostgreSQL

    """
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=db_name
    )


def ensure_database_exists(db_name):
    """
    Проверить наличие БД db_name и создать её при отсутствии

    Функция подключается к системной базе данных 'postgres' и проверяет,
    существует ли база данных с указанным именем. Если не существует -
    создаёт новую базу данных. Это необходимо для автоматической настройки
    приложения при первом запуске.

    Args:
        db_name (str): Имя базы данных, которую нужно проверить/создать

    Returns:
        bool: True - база данных существует или успешно создана,
              False - произошла ошибка при создании

    """
    conn = get_db_connection("postgres")
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if not cur.fetchone():
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
                print(f"✅ База данных '{db_name}' создана")
            else:
                print(f"ℹ️ База данных '{db_name}' уже существует")
    finally:
        conn.close()


def init_database(db_name):
    """
    Инициализировать структуру базы данных: создать все необходимые таблицы и индексы.

    Функция создаёт три основные таблицы для работы приложения:
    - users: хранение информации о пользователях
    - words: хранение слов (общих и персональных)
    - user_word_stats: статистика изучения слов пользователями

    Также создаются индексы для оптимизации часто используемых запросов.
    Если таблицы уже существуют, они не будут пересозданы (используется IF NOT EXISTS).

    Args:
        db_name (str): Имя базы данных, в которой нужно создать таблицы

    Returns:
        bool: True - таблицы успешно созданы/проверены,
              False - произошла ошибка

    """
    conn = get_db_connection(db_name)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS words (
                    id SERIAL PRIMARY KEY,
                    russian_word VARCHAR(255) NOT NULL,
                    english_word VARCHAR(255) NOT NULL,
                    word_type VARCHAR(50) NOT NULL DEFAULT 'noun',
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    is_common BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE (russian_word, english_word, user_id)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_word_stats (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    word_id INTEGER NOT NULL REFERENCES words(id) ON DELETE CASCADE,
                    correct_answers INTEGER NOT NULL DEFAULT 0,
                    total_answers INTEGER NOT NULL DEFAULT 0,
                    last_answer_correct BOOLEAN,
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE (user_id, word_id)
                );
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_words_user_id ON words(user_id);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_words_is_common ON words(is_common);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_stats_user_id ON user_word_stats(user_id);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_stats_word_id ON user_word_stats(word_id);
            """)

            conn.commit()
            print("✅ Таблицы готовы")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.rollback()
    finally:
        conn.close()

def fill_common_words(filepath='data/common_words.json'):
    """
    Заполнить таблицу words первоначальным набором слов из JSON-файла

    Функция загружает общие слова из JSON-файла и добавляет их в таблицу words
    с флагом is_common = TRUE и user_id = NULL. Перед добавлением проверяет,
    существует ли уже слово в общем словаре, чтобы избежать дубликатов.

    Args:
        filepath (str): Путь к JSON-файлу со словами.
                        По умолчанию 'data/common_words.json'

    Returns:
        int: Количество успешно добавленных слов, или None в случае ошибки

    """
    conn = get_db_connection(DB_NAME)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'words'
                );
            """)
            if not cur.fetchone()[0]:
                print("Таблица 'words' не существует. Запустите init_database() сначала.")
                return

            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    words_data = json.load(file)
            except FileNotFoundError:
                print(f"Файл не найден: {filepath}")
                return
            except json.JSONDecodeError as e:
                print(f"Ошибка чтения JSON-файла {filepath}: {e}")
                return

            inserted = 0
            for word in words_data:
                russian_word = word.get('russian_word')
                english_word = word.get('english_word')
                word_type = word.get('word_type')

                # Пропускаем запись, если обязательные поля отсутствуют
                if not all([russian_word, english_word, word_type]):
                    print(f"Пропущена некорректная запись: {word}")
                    continue

                cur.execute("""
                    SELECT 1
                    FROM words
                    WHERE russian_word = %s
                      AND english_word = %s
                      AND is_common = TRUE;
                """, (russian_word, english_word))

                if cur.fetchone():
                    continue

                cur.execute("""
                    INSERT INTO words (russian_word, english_word, word_type, user_id, is_common)
                    VALUES (%s, %s, %s, NULL, TRUE);
                """, (russian_word, english_word, word_type))

                inserted += 1

            conn.commit()
            print(f"Заполнено {inserted} общих слов в таблицу words.")
    except Exception as e:
        print(f"Ошибка: {e}")
        conn.rollback()
    finally:
        conn.close()


def login_user(username):
    """
    Выполнить вход пользователя в систему.

    Функция реализует автоматическую регистрацию: если пользователь с указанным
    именем существует - возвращает его ID, если нет - создаёт нового пользователя
    и возвращает его ID. Это упрощает процесс авторизации - не нужно отдельной
    регистрации.

    Args:
        username (str): Имя пользователя (будет автоматически очищено от пробелов)

    Returns:
        int | None: ID пользователя (существующего или нового) или None в случае ошибки

    """
    username = username.strip()
    if not username:
        return None

    conn = get_db_connection(DB_NAME)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username = %s;", (username,))
            row = cur.fetchone()
            if row:
                return row[0]

            cur.execute(
                "INSERT INTO users (username) VALUES (%s) RETURNING id;",
                (username,)
            )
            user_id = cur.fetchone()[0]
            conn.commit()
            return user_id
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка login_user: {e}")
        return None
    finally:
        conn.close()


def get_user_words(user_id):
    """
    Получить все слова пользователя (общие + персональные)

    Функция возвращает комбинированный список слов, включающий:
    - Все общие слова (is_common = TRUE, доступны всем пользователям)
    - Персональные слова пользователя (is_common = FALSE, user_id = указанный)

    Args:
        user_id (int): ID пользователя, чьи персональные слова нужно получить

    Returns:
        list: Список словарей с данными слов. Каждый словарь содержит:
              - id (int): Уникальный идентификатор слова
              - russian_word (str): Слово на русском языке
              - english_word (str): Перевод на английский язык
              - word_type (str): Тип слова (noun, adjective, verb и т.д.)
              - is_common (bool): True - общее слово, False - персональное
              - user_id (int | None): ID пользователя (NULL для общих слов)

              При отсутствии слов возвращает пустой список []

    """
    conn = get_db_connection(DB_NAME)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, russian_word, english_word, word_type, is_common, user_id
                FROM words
                WHERE is_common = TRUE OR user_id = %s
                ORDER BY is_common DESC, id ASC;
            """, (user_id,))
            rows = cur.fetchall()

            return [
                {
                    "id": row[0],
                    "russian_word": row[1],
                    "english_word": row[2],
                    "word_type": row[3],
                    "is_common": row[4],
                    "user_id": row[5]
                }
                for row in rows
            ]
    except Exception as e:
        print(f"❌ Ошибка get_user_words: {e}")
        return []
    finally:
        conn.close()


def check_word_exists(user_id, russian_word, english_word):
    """
    Проверить, существует ли слово у пользователя или в общем списке

    Args:
        user_id (int): ID пользователя
        russian_word (str): Русское слово
        english_word (str): Английский перевод

    Returns:
        str: None если слово не существует
             "common" - слово есть в общем словаре
             "personal" - слово есть в персональном словаре пользователя

    """
    russian_lower = russian_word.strip().lower()
    english_lower = english_word.strip().lower()

    conn = get_db_connection(DB_NAME)
    try:
        with conn.cursor() as cur:
            # Проверяем общее слово
            cur.execute("""
                SELECT 1
                FROM words
                WHERE is_common = TRUE
                  AND russian_word = %s
                  AND english_word = %s;
            """, (russian_lower, english_lower))

            if cur.fetchone():
                return "common"

            # Проверяем персональное слово
            cur.execute("""
                SELECT 1
                FROM words
                WHERE user_id = %s
                  AND russian_word = %s
                  AND english_word = %s;
            """, (user_id, russian_lower, english_lower))

            if cur.fetchone():
                return "personal"

            return None
    except Exception as e:
        print(f"❌ Ошибка check_word_exists: {e}")
        return None
    finally:
        conn.close()


def add_personal_word(user_id, russian_word, english_word, word_type="noun"):
    """
    Добавить персональное слово для пользователя
    Проверить, нет ли уже такого слова

    Args:
        user_id (int): ID пользователя
        russian_word (str): Русское слово
        english_word (str): Английский перевод
        word_type (str): Тип слова (noun, verb, adjective, etc.). По умолчанию "noun"

    Returns:
        bool: True - слово успешно добавлено, False - слово уже существует или ошибка

    """
    russian_word = russian_word.strip().lower()
    english_word = english_word.strip().lower()

    if not russian_word or not english_word:
        return False

    conn = get_db_connection(DB_NAME)
    try:
        with conn.cursor() as cur:
            # Проверяем, есть ли такое слово у пользователя (персональное)
            cur.execute("""
                SELECT 1
                FROM words
                WHERE user_id = %s
                  AND russian_word = %s
                  AND english_word = %s;
            """, (user_id, russian_word, english_word))

            if cur.fetchone():
                return False

            # Проверяем, есть ли такое слово в общем списке
            cur.execute("""
                SELECT 1
                FROM words
                WHERE is_common = TRUE
                  AND russian_word = %s
                  AND english_word = %s;
            """, (russian_word, english_word))

            if cur.fetchone():
                return False

            cur.execute("""
                INSERT INTO words (russian_word, english_word, word_type, user_id, is_common)
                VALUES (%s, %s, %s, %s, FALSE)
                RETURNING id;
            """, (russian_word, english_word, word_type, user_id))

            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка add_personal_word: {e}")
        return False
    finally:
        conn.close()


def delete_personal_word(user_id, word_id):
    """
    Удалить персональное слово пользователя

    Функция удаляет слово только если оно принадлежит указанному пользователю
    и не является общим словом (is_common = FALSE). Общие слова удалить нельзя.

    Args:
        user_id (int): ID пользователя, владельца слова
        word_id (int): ID слова для удаления

    Returns:
        bool: True - слово успешно удалено,
              False - слово не найдено или ошибка

    """
    conn = get_db_connection(DB_NAME)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM words
                WHERE id = %s
                  AND user_id = %s
                  AND is_common = FALSE
                RETURNING id;
            """, (word_id, user_id))

            deleted = cur.fetchone()
            conn.commit()
            return deleted is not None
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка delete_personal_word: {e}")
        return False
    finally:
        conn.close()


def update_stats(user_id, word_id, is_correct):
    """
    Обновить статистику изучения слова

    Функция обновляет или создаёт запись статистики для пары пользователь-слово.
    При каждом ответе увеличивается счётчик total_answers, а correct_answers
    увеличивается только при правильном ответе.

    Args:
        user_id (int): ID пользователя, который отвечал
        word_id (int): ID слова, по которому был ответ
        is_correct (bool): True - ответ правильный, False - неправильный

    Returns:
        None

    """
    conn = get_db_connection(DB_NAME)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_word_stats (
                    user_id,
                    word_id,
                    correct_answers,
                    total_answers,
                    last_answer_correct,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (user_id, word_id)
                DO UPDATE SET
                    correct_answers = user_word_stats.correct_answers + EXCLUDED.correct_answers,
                    total_answers = user_word_stats.total_answers + 1,
                    last_answer_correct = EXCLUDED.last_answer_correct,
                    updated_at = NOW();
            """, (user_id, word_id, 1 if is_correct else 0, 1, is_correct))

            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка update_stats: {e}")
    finally:
        conn.close()


def get_statistics(user_id):
    """
    Получить полную статистику изучения слов для пользователя.

    Функция агрегирует данные из таблицы user_word_stats и возвращает
    сводную статистику по всем словам, которые пользователь пытался учить.

    Args:
        user_id (int): ID пользователя для получения статистики

    Returns:
        dict: Словарь со следующими ключами:
              - total_answers (int): Общее количество попыток ответов
              - correct_answers (int): Количество правильных ответов
              - studied_words (int): Количество уникальных изученных слов
              - accuracy (float): Процент правильных ответов (0-100)

    """
    conn = get_db_connection(DB_NAME)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COALESCE(SUM(total_answers), 0) AS total_answers,
                    COALESCE(SUM(correct_answers), 0) AS correct_answers,
                    COUNT(*) AS studied_words
                FROM user_word_stats
                WHERE user_id = %s;
            """, (user_id,))
            row = cur.fetchone()

            total_answers = row[0] or 0
            correct_answers = row[1] or 0
            studied_words = row[2] or 0
            accuracy = round((correct_answers / total_answers * 100), 2) if total_answers else 0

            return {
                "total_answers": total_answers,
                "correct_answers": correct_answers,
                "studied_words": studied_words,
                "accuracy": accuracy
            }
    except Exception as e:
        print(f"❌ Ошибка get_statistics: {e}")
        return {
            "total_answers": 0,
            "correct_answers": 0,
            "studied_words": 0,
            "accuracy": 0
        }
    finally:
        conn.close()

if __name__ == '__main__':
    ensure_database_exists(DB_NAME)
    init_database(DB_NAME)
    fill_common_words()

