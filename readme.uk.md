# CodeCraft Agents (Агенти-Творці Коду)

![CodeCraft Agents Banner](assets/logo.svg)

> Перетворення описів завдань природною мовою у повноцінні, протестовані та контейнеризовані програмні рішення

## 🌐 Інші мови 
- [README англійською](readme.md)


## 🚀 Огляд

CodeCraft Agents — це передова мультиагентна система штучного інтелекту, яка автоматично перетворює описи природною мовою на готовий до використання код. Проект демонструє потужність спеціалізованих ШІ-агентів, що працюють у співпраці для забезпечення повного життєвого циклу розробки програмного забезпечення — від аналізу завдання до розгортання.

**Примітка:** Це прототип, наразі оптимізований для однофайлових додатків.

## ✨ Ключові особливості

- **Повністю автоматизована генерація коду** — Від концепції до робочого коду з мінімальним втручанням людини
- **Мультиагентна архітектура** — Спеціалізовані агенти для кожного етапу розробки
- **Комплексна верифікація** — Вбудоване тестування, валідація та цикли зворотного зв'язку
- **Інтеграція з Docker** — Автоматична контейнеризація згенерованих додатків
- **Екстракція знань** — Постійне навчання на основі згенерованих рішень

## 🤖 Архітектура системи агентів

Наша система використовує спеціалізованого агента для кожного етапу процесу розробки:

1. **DecomposerAgent** — Розбиває опис завдання на структуровані модулі та інтерфейси
2. **ValidatorAgent** — Перевіряє повноту та правильність плану
3. **ConsistencyAgent** — Перевіряє узгодженість типів даних і логіки між модулями
4. **CodeGeneratorAgent** — Створює код на основі затвердженого плану
5. **CodeExtractorAgent** — Зберігає код у відповідні файли
6. **DockerRunnerAgent** — Генерує конфігурації Dockerfile та docker-compose
7. **TesterAgent** — Створює тестові випадки та перевіряє функціональність додатку
8. **DocumentationAgent** — Генерує вичерпну документацію з використання
9. **MonitorAgent** і **CoordinatorAgent** — Контролюють процес та керують переходами робочого процесу

## 🔄 Як це працює

Коли ви надаєте опис завдання для CodeCraft Agents, система виконує такий робочий процес:

1. **Аналіз завдання** — DecomposerAgent розбиває завдання на керовані компоненти
2. **Планування та валідація** — Система створює та перевіряє комплексний план розробки
3. **Генерація коду** — На основі затвердженого плану створюється чистий, ефективний код
4. **Тестування та контейнеризація** — Код ретельно тестується та пакується в контейнер Docker
5. **Документація** — Автоматично генерується вичерпна документація з використання

Весь процес регулюється нашим адаптивним циклом зворотного зв'язку, який забезпечує високу якість результату завдяки кільком рівням верифікації.

## 📋 Приклад використання

За простим вхідним завданням:

```
Створити API-сервер з маршрутом /sum, який приймає два GET-параметри a і b (числа) та повертає їх суму. Використовувати aiohttp.
```

CodeCraft Agents створить:

1. Робочий Python-додаток з обробкою помилок та належною структурою
2. Докеризоване середовище для легкого розгортання
3. Набір тестів для перевірки функціональності
4. Вичерпну документацію з використання та розгортання

## 🛠️ Технічна реалізація

Система побудована на модульній архітектурі, яка включає:

- Розширену інженерію промптів для спеціалізованих ролей агентів
- Механізми верифікації для контролю якості
- Адаптивні цикли зворотного зв'язку для виправлення помилок
- Ізольовані середовища виконання для тестування
- Векторну базу знань для розширення контексту

## 🔍 Поточні обмеження

Як прототип, CodeCraft Agents наразі має деякі обмеження:

- Оптимізовано для однофайлових Python-додатків
- Найкраще працює з веб-API та базовими утилітами
- Обмежена складність відносин баз даних та аутентифікації
- Ще не підтримує повномасштабні багатофайлові проекти

## 🚀 Початок роботи

### Передумови

- Python 3.9 або вище
- Docker та docker-compose
- Доступ до API OpenRouter
- Qdrant для векторного сховища

### Встановлення

1. Клонуйте репозиторій:
```bash
git clone https://github.com/yourusername/codecraft-agents.git
cd codecraft-agents
```

2. Встановіть залежності:
```bash
pip install -r requirements.txt
```

3. Запустіть Qdrant за допомогою docker-compose:
```bash
docker-compose up -d
```

4. Встановіть ключ API OpenRouter:
```bash
export OPENROUTER_API_KEY=your_key_here
```

### Використання

Запустіть систему з описом завдання:

```bash
python main.py
```

За замовчуванням система згенерує код для зразкового завдання. Щоб налаштувати, відредагуйте змінну `task` у файлі `main.py`.

Вихідні файли будуть створені в директорії `project/`.

## 📚 Документація

Для більш детальної інформації про архітектуру та компоненти системи, дивіться:

- [Архітектура агентів](docs/agent-architecture.md)
- [Деталі інженерії промптів](docs/prompts.md)
- [Система верифікації](docs/verification.md)
- [Механізм циклу зворотного зв'язку](docs/feedback-loop.md)


## 📈 Майбутня дорожня карта

- Підтримка багатофайлових проектів
- Додаткові мови програмування
- Генерація фронтенд-коду
- Більш складні інтеграції баз даних
- Генерація CI/CD-пайплайнів
- Покращена екстракція та повторне використання знань
- Підтримка React та інших фронтенд-фреймворків

## 📄 Ліцензія

Цей проект ліцензовано за Apache License 2.0 — деталі дивіться у файлі [LICENSE.md](LICENSE.md).

## 🤝 Внесок

Внески вітаються! Будь ласка, не соромтеся надсилати Pull Request.

---

<p align="center">
  <small>Створено з ❤️ командою CodeCraft Agents</small>
</p>
