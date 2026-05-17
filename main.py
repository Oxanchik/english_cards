"""Learn English by Cards - Приложение для изучения английского языка"""
import random

from dotenv import load_dotenv
import streamlit as st

from models import (
    DB_NAME,
    ensure_database_exists,
    init_database,
    fill_common_words,
    login_user,
    get_user_words,
    add_personal_word,
    delete_personal_word,
    update_stats,
    get_statistics,
    check_word_exists
)

load_dotenv()

# ============================================================
# НАСТРОЙКА СТРАНИЦЫ
# ============================================================

st.set_page_config(
    page_title="EnglishCards - Изучение английского",
    page_icon="📚",
    layout="wide"
)

# ============================================================
# ИНТЕРФЕЙС ПРИЛОЖЕНИЯ
# ============================================================

def init_session_state():
    """
    Инициализировать все переменные состояния Streamlit.

    Функция проверяет существование каждой переменной в st.session_state и
    устанавливает начальное значение, если переменная отсутствует. Это необходимо
    для сохранения состояния между перезагрузками страницы и взаимодействиями
    пользователя с интерфейсом.

    Переменные состояния:
        user_id (int | None): ID авторизованного пользователя
        username (str): Имя авторизованного пользователя
        current_word_id (int | None): ID текущего слова в тренировке
        current_question (dict | None): Данные текущего слова
        current_options (list): Варианты ответов для текущего вопроса
        answer_message (str): Сообщение о результате ответа
        answer_status (str | None): Статус ответа ("success" или "error")
        db_initialized (bool): Флаг инициализации базы данных
        show_schema (bool): Флаг отображения схемы БД
        add_word_message (str): Сообщение при добавлении слова
        add_word_status (str | None): Статус добавления слова
        delete_word_message (str): Сообщение при удалении слова
        delete_word_status (str | None): Статус удаления слова
        delete_word_refresh (bool): Флаг обновления после удаления

    Returns:
        None

    """
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "current_word_id" not in st.session_state:
        st.session_state.current_word_id = None
    if "current_question" not in st.session_state:
        st.session_state.current_question = None
    if "current_options" not in st.session_state:
        st.session_state.current_options = []
    if "answer_message" not in st.session_state:
        st.session_state.answer_message = ""
    if "answer_status" not in st.session_state:
        st.session_state.answer_status = None
    if "db_initialized" not in st.session_state:
        st.session_state.db_initialized = False
    if "show_schema" not in st.session_state:
        st.session_state.show_schema = False
    if "add_word_message" not in st.session_state:
        st.session_state.add_word_message = ""
    if "add_word_status" not in st.session_state:
        st.session_state.add_word_status = None
    if "delete_word_message" not in st.session_state:
        st.session_state.delete_word_message = ""
    if "delete_word_status" not in st.session_state:
        st.session_state.delete_word_status = None
    if "delete_word_refresh" not in st.session_state:
        st.session_state.delete_word_refresh = False
    if "answered" not in st.session_state:
        st.session_state.answered = False
    if "correct_option" not in st.session_state:
        st.session_state.correct_option = None


def generate_options(words):
    """
    Сгенерировать варианты ответов для текущего слова.

    Функция выбирает случайное слово из списка и создаёт 4 варианта перевода:
    1 правильный и 3 неправильных. Неправильные варианты берутся из других слов
    в списке, а при нехватке используются слова-заполнители.

    Args:
        words (list): Список слов для тренировки (каждый элемент - словарь с полями
                      id, russian_word, english_word, word_type и т.д.)

    Returns:
        None

    """
    if not words:
        st.session_state.current_question = None
        st.session_state.current_options = []
        st.session_state.current_word_id = None
        st.session_state.answered = False
        st.session_state.correct_option = None
        return

    word = random.choice(words)
    correct = word["english_word"]

    all_english = list({w["english_word"] for w in words if w["english_word"] != correct})
    random.shuffle(all_english)
    wrong_options = all_english[:3]

    while len(wrong_options) < 3:
        filler = random.choice(["apple", "water", "school", "friend", "home", "time"])
        if filler != correct and filler not in wrong_options:
            wrong_options.append(filler)

    options = wrong_options + [correct]
    random.shuffle(options)

    st.session_state.current_question = word
    st.session_state.current_word_id = word["id"]
    st.session_state.current_options = options
    st.session_state.answer_message = ""
    st.session_state.answer_status = None
    st.session_state.answered = False
    st.session_state.correct_option = correct


def handle_answer(selected_option):
    """
    Обработать ответ пользователя на текущий вопрос.

    Функция сравнивает выбранный вариант с правильным ответом, обновляет
    сообщение и статус в session_state, а также сохраняет статистику
    через update_stats().

    Args:
        selected_option (str): Выбранный пользователем вариант перевода

    Returns:
        None

   """
    if st.session_state.answered:
        return

    correct_answer = st.session_state.current_question["english_word"]

    if selected_option == correct_answer:
        st.session_state.answer_message = "✅ Верно!"
        st.session_state.answer_status = "success"
        st.session_state.answered = True
        st.session_state.correct_option = correct_answer
        update_stats(
            st.session_state.user_id,
            st.session_state.current_question["id"],
            True
        )
    else:
        st.session_state.answer_message = "❌ Неверно. Попробуй ещё раз."
        st.session_state.answer_status = "error"
        st.session_state.answered = True
        st.session_state.correct_option = correct_answer
        update_stats(
            st.session_state.user_id,
            st.session_state.current_question["id"],
            False
        )


def render_sidebar():
    """
    Отрисовать боковую панель с авторизацией

    Функция создаёт интерфейс для входа/выхода пользователя:
    - Поле ввода имени пользователя
    - Кнопка "Войти" (для неавторизованных)
    - Приветствие и кнопка "Выйти" (для авторизованных)

    Returns:
        None

    """
    st.sidebar.header("Авторизация")

    if st.session_state.user_id is None:
        username = st.sidebar.text_input("Введи имя пользователя", value=st.session_state.username)
        if st.sidebar.button("Войти"):
            user_id = login_user(username)
            if user_id is not None:
                st.session_state.user_id = int(user_id)
                st.session_state.username = username.strip()
                st.session_state.answer_message = ""
                st.session_state.answer_status = None
                st.session_state.add_word_message = ""
                st.session_state.add_word_status = None
                st.session_state.delete_word_message = ""
                st.session_state.delete_word_status = None
                st.session_state.delete_word_refresh = False
                st.rerun()
            else:
                st.sidebar.error("Не удалось войти.")
    else:
        st.sidebar.success(f"Пользователь: {st.session_state.username}")
        if st.sidebar.button("Выйти"):
            st.session_state.user_id = None
            st.session_state.username = ""
            st.session_state.current_word_id = None
            st.session_state.current_question = None
            st.session_state.current_options = []
            st.session_state.answer_message = ""
            st.session_state.answer_status = None
            st.session_state.add_word_message = ""
            st.session_state.add_word_status = None
            st.session_state.delete_word_message = ""
            st.session_state.delete_word_status = None
            st.session_state.delete_word_refresh = False
            st.rerun()


def render_study_tab(words):
    """
    Отрисовать вкладку изучения слов (тренировка)

    Функция создаёт интерфейс для тренировки:
    - Отображение русского слова для перевода
    - 4 кнопки с вариантами перевода
    - Обработка правильных/неправильных ответов
    - Кнопка "Следующее слово"

    Args:
        words (list): Список слов пользователя (общие + персональные)

    Returns:
        None

    """
    st.subheader("Тренировка")

    if not words:
        st.info("Список слов пуст. Добавьте первое слово во вкладке 'Добавить слово'.")
        return

    if st.session_state.current_question is None:
        generate_options(words)

    word = st.session_state.current_question
    if not word:
        st.warning("Не удалось выбрать слово.")
        return

    st.markdown(f"### Переведи слово: **{word['russian_word']}**")

    cols = st.columns(2)
    for i, option in enumerate(st.session_state.current_options):
        with cols[i % 2]:
            if st.session_state.answered and option == st.session_state.correct_option:
                st.success(option)
            else:
                clicked = st.button(
                    option,
                    key=f"option_{word['id']}_{option}",
                    disabled=st.session_state.answered
                )
                if clicked:
                    handle_answer(option)
                    st.rerun()

    if st.session_state.answer_message:
        if st.session_state.answer_status == "success":
            st.success(st.session_state.answer_message)
        else:
            st.error(st.session_state.answer_message)

    if st.session_state.answered:
        st.info("Нажми «Следующее слово», чтобы продолжить.")

    if st.button("Следующее слово", type="primary"):
        generate_options(words)
        st.rerun()


def render_add_word_tab():
    """
    Отрисовать вкладку добавления персонального слова

    Функция создаёт форму для добавления нового слова в персональный словарь
    пользователя. Проверяет, не существует ли уже такое слово в общем или
    персональном словаре.

    Returns:
        None

    """
    st.subheader("Добавить слово")

    if "add_word_message" not in st.session_state:
        st.session_state.add_word_message = ""
    if "add_word_status" not in st.session_state:
        st.session_state.add_word_status = None

    if st.session_state.add_word_message:
        if st.session_state.add_word_status == "success":
            st.success(st.session_state.add_word_message)
        elif st.session_state.add_word_status == "warning":
            st.warning(st.session_state.add_word_message)
        else:
            st.error(st.session_state.add_word_message)

    with st.form("add_word_form", clear_on_submit=True):
        russian_word = st.text_input("Русское слово", key="add_russian_word")
        english_word = st.text_input("Английский перевод", key="add_english_word")
        word_type = st.selectbox("Часть речи", ["noun", "adjective", "verb", "other"], index=0)
        submitted = st.form_submit_button("Добавить")

        if submitted:
            if not russian_word.strip() or not english_word.strip():
                st.session_state.add_word_message = "Заполни оба поля."
                st.session_state.add_word_status = "error"
                st.rerun()

            # Проверяем существование слова
            exists_type = check_word_exists(
                st.session_state.user_id,
                russian_word,
                english_word
            )

            if exists_type == "common":
                st.session_state.add_word_message = (
                    f"ℹ️ Слово '{russian_word} → {english_word}' уже есть в общем словаре. "
                    f"Оно доступно всем пользователям, добавлять не нужно."
                )
                st.session_state.add_word_status = "warning"

            elif exists_type == "personal":
                st.session_state.add_word_message = "ℹ️ Это слово уже есть в твоем персональном словаре."
                st.session_state.add_word_status = "warning"

            else:
                # Слово не существует - можно добавлять
                ok = add_personal_word(
                    st.session_state.user_id,
                    russian_word,
                    english_word,
                    word_type
                )
                if ok:
                    count = len(get_user_words(st.session_state.user_id))
                    st.session_state.add_word_message = (
                        f"✅ Слово добавлено. Теперь у тебя {count} слов(а) в тренажёре."
                    )
                    st.session_state.add_word_status = "success"
                else:
                    st.session_state.add_word_message = "⚠️ Не удалось добавить слово."
                    st.session_state.add_word_status = "warning"

            st.rerun()


def render_delete_word_tab(words):
    """
    Отрисовать вкладку удаления персонального слова

    Функция создаёт интерфейс для удаления слов из персонального словаря:
    - Выпадающий список с персональными словами пользователя
    - Кнопка удаления с подтверждением
    - Уведомление о результате операции

    Args:
        words (list): Список всех слов пользователя (для фильтрации персональных)

    Returns:
        None

    """
    st.subheader("Удалить слово")

    if "delete_word_message" not in st.session_state:
        st.session_state.delete_word_message = ""
    if "delete_word_status" not in st.session_state:
        st.session_state.delete_word_status = None
    if "delete_word_refresh" not in st.session_state:
        st.session_state.delete_word_refresh = False

    personal_words = [
        w for w in words
        if not w["is_common"] and w["user_id"] == st.session_state.user_id
    ]

    if st.session_state.delete_word_message:
        if st.session_state.delete_word_status == "success":
            st.success(st.session_state.delete_word_message)
        elif st.session_state.delete_word_status == "error":
            st.error(st.session_state.delete_word_message)

    if not personal_words:
        st.info("У тебя пока нет персональных слов для удаления.")
        return

    options = {
        f"{w['russian_word']} → {w['english_word']}": w["id"]
        for w in personal_words
    }

    with st.form("delete_word_form", clear_on_submit=True):
        selected_label = st.selectbox("Выбери слово", list(options.keys()), key="delete_word_select")
        submitted = st.form_submit_button("Удалить")

        if submitted:
            word_id = options[selected_label]
            if delete_personal_word(st.session_state.user_id, word_id):
                st.session_state.delete_word_message = "✅ Слово удалено из твоего тренажера."
                st.session_state.delete_word_status = "success"
            else:
                st.session_state.delete_word_message = "⚠️ Не удалось удалить слово."
                st.session_state.delete_word_status = "error"

            st.rerun()


def render_statistics_tab(user_id):
    """
    Отрисовать вкладку статистики изучения слов

    Функция отображает агрегированную статистику пользователя:
    - Количество правильных ответов
    - Общее количество попыток
    - Процент точности (правильные ответы / общее число ответов)
    - Количество изученных слов

    Args:
        user_id (int): ID пользователя для получения статистики

    Returns:
        None

    """
    st.subheader("Статистика")

    stats = get_statistics(user_id)

    col1, col2, col3 = st.columns(3)
    col1.metric("Правильных ответов", stats["correct_answers"])
    col2.metric("Всего попыток", stats["total_answers"])
    col3.metric("Точность", f"{stats['accuracy']}%")

    st.write(f"Пройденных слов: **{stats['studied_words']}**")



def render_schema():
    """
    Реализовать отображение схемы базы данных

    Функция отображает изображение со схемой базы данных из файла.

    Returns:
        None

    """
    st.subheader("Схема базы данных")
    st.image("images/English_cards_db_scheme_pgAdmin4.png", width="stretch")


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

def main_eng_cards():
    """
    Главная функция приложения EnglishCards

    Функция управляет всем приложением:
    1. Инициализирует session_state
    2. Проверяет и создаёт базу данных при первом запуске
    3. Отображает заголовок и приветствие
    4. Рендерит боковую панель с авторизацией
    5. Для авторизованных пользователей показывает вкладки
    6. Для неавторизованных показывает приглашение войти

    Returns:
        None

    """
    init_session_state()

    if not st.session_state.db_initialized:
        ensure_database_exists(DB_NAME)
        init_database(DB_NAME)
        fill_common_words()
        st.session_state.db_initialized = True

    st.title("📚 Learn English by Cards - Изучай английский с удовольствием!")

    st.markdown(
        """
        Привет 👋 Давай попрактикуемся в английском языке. 
        Тренировки можешь проходить в удобном для себя темпе.

        У тебя есть возможность использовать тренажёр, как конструктор, и собирать свою собственную базу для обучения.
        
        Для этого воспользуйся инструментами:
        
        добавить слово ➕, удалить слово 🗑️.


        Ну что, начнём ⬇️
        """
    )

    render_sidebar()

    if st.session_state.user_id:
        words = get_user_words(st.session_state.user_id)
        tab1, tab2, tab3, tab4 = st.tabs([
            "📖 Изучение",
            "➕ Добавить слово",
            "🗑️ Удалить слово",
            "📊 Статистика"
        ])

        with tab1:
            render_study_tab(words)

        with tab2:
            render_add_word_tab()

        with tab3:
            render_delete_word_tab(words)

        with tab4:
            render_statistics_tab(st.session_state.user_id)

        st.divider()
        if st.button("Схема базы данных"):
            st.session_state.show_schema = not st.session_state.show_schema

        if st.session_state.show_schema:
            render_schema()

    else:
        st.info("Войди в систему, чтобы начать обучение. Введи имя пользователя в окошке авторизации и нажми кнопку 'Войти'")


if __name__ == "__main__":
    main_eng_cards()



