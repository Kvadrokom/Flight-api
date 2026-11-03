// ─────────────────────────────────────────────────────────────
//  Константы
// ─────────────────────────────────────────────────────────────

const AIRLINES = {
    SU: 'Аэрофлот', S7: 'S7', U6: 'Уральские авиалинии', DP: 'Победа',
    UT: 'ЮТэйр', N4: 'Nordwind', FV: 'Россия', '5N': 'Smartavia',
    A4: 'Азимут', R3: 'Якутия', WZ: 'Red Wings',
    TK: 'Turkish Airlines', PC: 'Pegasus', FZ: 'Flydubai',
    EK: 'Emirates', QR: 'Qatar Airways', J2: 'Azerbaijan Airlines',
    A9: 'Georgian Airways', '3F': 'FlyOne Armenia', CZ: 'China Southern',
    HY: 'Uzbekistan Airways', KC: 'Air Astana',
};

const CITY_SELECTS = ['origin', 'destination', 'cal-origin', 'cal-destination', 'pop-origin'];

const MONTHS_RU = [
    'январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
    'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь',
];

let CITY_NAMES = {};

const $ = (id) => document.getElementById(id);


// ─────────────────────────────────────────────────────────────
//  Утилиты
// ─────────────────────────────────────────────────────────────

function cityLabel(code) {
    if (!code) return '—';
    const name = CITY_NAMES[code];
    return name ? `${name} (${code})` : code;
}

function setStatusFor(el, text, type = 'info') {
    el.hidden = !text;
    el.textContent = text;
    el.className = `status ${type}`;
}

function formatDateTime(iso) {
    if (!iso) return null;
    try {
        const d = new Date(iso);
        return d.toLocaleString('ru-RU', {
            day: 'numeric', month: 'short', year: 'numeric',
            hour: '2-digit', minute: '2-digit',
        });
    } catch {
        return iso;
    }
}

function formatDuration(minutes) {
    if (!minutes) return null;
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return m ? `${h} ч ${m} мин` : `${h} ч`;
}

function formatMonth(yyyymm) {
    // "2026-12" → "декабрь 2026"
    if (!yyyymm) return '';
    const [y, m] = yyyymm.split('-').map(Number);
    if (!y || !m || m < 1 || m > 12) return yyyymm;
    return `${MONTHS_RU[m - 1]} ${y}`;
}


// ─────────────────────────────────────────────────────────────
//  Загрузка городов
// ─────────────────────────────────────────────────────────────

async function loadCities() {
    const res = await fetch('/reference/cities');
    if (!res.ok) throw new Error('Не удалось загрузить список городов');
    return await res.json();
}

function populateSelects(cities) {
    for (const selectId of CITY_SELECTS) {
        const select = $(selectId);
        if (!select) continue;
        const sorted = [...cities].sort((a, b) => a.name.localeCompare(b.name, 'ru'));
        for (const city of sorted) {
            const opt = document.createElement('option');
            opt.value = city.code;
            opt.textContent = `${city.name} (${city.code})`;
            select.appendChild(opt);
        }
    }
}


// ─────────────────────────────────────────────────────────────
//  Якорные табы + подсветка при скролле
// ─────────────────────────────────────────────────────────────

function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    const sections = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
        });
    });

    const onScroll = () => {
        const threshold = 100;
        let current = sections[0]?.id;
        for (const section of sections) {
            if (section.getBoundingClientRect().top <= threshold) {
                current = section.id;
            }
        }
        tabs.forEach(t => {
            t.classList.toggle('active', t.getAttribute('href') === `#${current}`);
        });
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
}


// ─────────────────────────────────────────────────────────────
//  Карточки результатов
// ─────────────────────────────────────────────────────────────

function renderResults(entries, container, statusEl) {
    container.innerHTML = '';

    if (!entries.length) {
        setStatusFor(statusEl, 'По этому маршруту нет данных в кэше. Попробуйте другие города или даты.', 'info');
        return;
    }

    setStatusFor(statusEl, `Найдено вариантов: ${entries.length}`, 'info');

    for (const entry of entries) {
        const card = document.createElement('div');
        card.className = 'card';

        const airlineName = AIRLINES[entry.airline] || entry.airline || '—';
        const depart = formatDateTime(entry.departure_at) || '—';
        const ret = entry.return_at ? formatDateTime(entry.return_at) : null;

        const isRoundTrip = entry.return_at != null;
        const badge = isRoundTrip
            ? '<span class="badge badge-round">туда-обратно</span>'
            : '<span class="badge badge-oneway">в одну сторону</span>';

        const transfers = entry.transfers === 0 ? 'без пересадок'
            : entry.transfers != null ? `пересадок: ${entry.transfers}` : '';

        const duration = entry.duration ? `в пути: ${formatDuration(entry.duration)}` : '';
        const meta = [airlineName, transfers, duration].filter(Boolean).join(' · ');

        const linkHtml = entry.link
            ? `<a href="${entry.link}" target="_blank" rel="noopener noreferrer">Купить</a>`
            : '';

        card.innerHTML = `
            <div class="card-info">
                <h3>${cityLabel(entry.origin)} → ${cityLabel(entry.destination)} ${badge}</h3>
                <p>${meta}</p>
                <p>Туда: ${depart}</p>
                ${ret ? `<p>Обратно: ${ret}</p>` : ''}
            </div>
            <div class="card-price">
                <span class="amount">${Math.round(entry.price).toLocaleString('ru-RU')} ₽</span>
                <span class="per-person">за 1 взрослого</span>
                ${linkHtml}
            </div>
        `;
        container.appendChild(card);
    }
}


// ─────────────────────────────────────────────────────────────
//  Поиск
// ─────────────────────────────────────────────────────────────

async function onSearchSubmit(e) {
    e.preventDefault();
    const statusEl = $('status');
    const resultsEl = $('results');
    resultsEl.innerHTML = '';

    const origin = $('origin').value;
    const destination = $('destination').value;
    const departDate = $('depart-date').value;
    const returnDate = $('return-date').value;

    if (!origin || !destination) {
        setStatusFor(statusEl, 'Выберите города вылета и прилёта', 'error');
        return;
    }
    if (origin === destination) {
        setStatusFor(statusEl, 'Города вылета и прилёта не должны совпадать', 'error');
        return;
    }
    if (returnDate && !departDate) {
        setStatusFor(statusEl, 'Укажите дату вылета, чтобы задать дату возврата', 'error');
        return;
    }

    const payload = { origin, destination };
    if (departDate) payload.depart_date = departDate;
    if (returnDate) payload.return_date = returnDate;
    if ($('one-way').checked) payload.one_way = true;

    $('submit-btn').disabled = true;
    setStatusFor(statusEl, 'Ищем билеты…', 'info');

    try {
        const res = await fetch('/prices/cheap', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!res.ok) {
            const errText = await res.text();
            throw new Error(`Ошибка ${res.status}: ${errText.slice(0, 200)}`);
        }
        const entries = await res.json();
        renderResults(entries, resultsEl, statusEl);
    } catch (err) {
        setStatusFor(statusEl, `Не удалось выполнить поиск: ${err.message}`, 'error');
    } finally {
        $('submit-btn').disabled = false;
    }
}


// ─────────────────────────────────────────────────────────────
//  Календарь цен
// ─────────────────────────────────────────────────────────────

function renderCalendar(days, container, statusEl, meta) {
    container.innerHTML = '';

    // Заголовок и легенда
    const header = document.createElement('div');
    header.className = 'calendar-header';

    const title = document.createElement('div');
    title.className = 'calendar-title';
    title.textContent = `Цены на ${meta.monthLabel}`;

    const legend = document.createElement('div');
    legend.className = 'calendar-legend';
    legend.innerHTML = meta.isRoundTrip
        ? '<span class="badge badge-round">туда-обратно</span> <span class="legend-note">(где доступны в кэше)</span>'
        : '<span class="badge badge-oneway">в одну сторону</span> <span class="legend-note">(за 1 взрослого)</span>';

    header.appendChild(title);
    header.appendChild(legend);
    container.appendChild(header);

    if (!days.length) {
        const empty = document.createElement('div');
        empty.className = 'calendar-empty';
        empty.textContent = 'Нет данных за этот месяц. Попробуйте другой месяц или маршрут.';
        container.appendChild(empty);
        setStatusFor(statusEl, '', 'info');
        return;
    }

    const min = Math.min(...days.map(d => d.price));
    setStatusFor(
        statusEl,
        `Дней с ценами: ${days.length}. Минимум: ${Math.round(min).toLocaleString('ru-RU')} ₽`,
        'info',
    );

    const grid = document.createElement('div');
    grid.className = 'calendar-grid';

    for (const d of days) {
        const cell = document.createElement('div');
        cell.className = 'cal-cell';
        if (d.price === min) cell.classList.add('cheapest');

        const dayNum = new Date(d.day).getDate();
        const mark = meta.isRoundTrip && d.return_at
            ? '<span class="cal-return" title="Есть дата возврата">⇄</span>'
            : '';

        cell.innerHTML = `
            <span class="cal-day">${dayNum}${mark}</span>
            <span class="cal-price">${Math.round(d.price).toLocaleString('ru-RU')} ₽</span>
        `;
        grid.appendChild(cell);
    }
    container.appendChild(grid);
}

async function onCalendarSubmit(e) {
    e.preventDefault();
    const statusEl = $('calendar-status');
    const resultsEl = $('calendar-results');
    resultsEl.innerHTML = '';
    setStatusFor(statusEl, '', 'info');

    const origin = $('cal-origin').value;
    const destination = $('cal-destination').value;
    const departDate = $('cal-month').value;
    const returnMonth = $('cal-return-month').value;

    if (!origin || !destination) {
        setStatusFor(statusEl, 'Выберите города вылета и прилёта', 'error');
        return;
    }
    if (origin === destination) {
        setStatusFor(statusEl, 'Города вылета и прилёта не должны совпадать', 'error');
        return;
    }
    if (!departDate) {
        setStatusFor(statusEl, 'Укажите месяц вылета — иначе непонятно, за какой период строить календарь', 'error');
        return;
    }

    const payload = { origin, destination, depart_date: departDate };
    if (returnMonth) payload.return_date = returnMonth;

    $('calendar-btn').disabled = true;
    setStatusFor(statusEl, 'Загружаем календарь…', 'info');

    try {
        const res = await fetch('/prices/calendar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!res.ok) {
            const errText = await res.text();
            throw new Error(`Ошибка ${res.status}: ${errText.slice(0, 200)}`);
        }
        const days = await res.json();

        renderCalendar(days, resultsEl, statusEl, {
            monthLabel: formatMonth(departDate),
            isRoundTrip: !!returnMonth,
        });
    } catch (err) {
        setStatusFor(statusEl, `Не удалось загрузить календарь: ${err.message}`, 'error');
    } finally {
        $('calendar-btn').disabled = false;
    }
}


// ─────────────────────────────────────────────────────────────
//  Популярные направления
// ─────────────────────────────────────────────────────────────

async function onPopularSubmit(e) {
    e.preventDefault();
    const statusEl = $('popular-status');
    const resultsEl = $('popular-results');
    resultsEl.innerHTML = '';

    const origin = $('pop-origin').value;
    const limit = parseInt($('pop-limit').value, 10);

    if (!origin) {
        setStatusFor(statusEl, 'Выберите город', 'error');
        return;
    }

    $('popular-btn').disabled = true;
    setStatusFor(statusEl, 'Загружаем популярные направления…', 'info');

    try {
        const res = await fetch('/prices/popular', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ origin, limit }),
        });
        if (!res.ok) {
            const errText = await res.text();
            throw new Error(`Ошибка ${res.status}: ${errText.slice(0, 200)}`);
        }
        const entries = await res.json();
        renderResults(entries, resultsEl, statusEl);
    } catch (err) {
        setStatusFor(statusEl, `Не удалось загрузить популярные: ${err.message}`, 'error');
    } finally {
        $('popular-btn').disabled = false;
    }
}


// ─────────────────────────────────────────────────────────────
//  Инициализация
// ─────────────────────────────────────────────────────────────

async function init() {
    initTabs();

    try {
        const cities = await loadCities();
        CITY_NAMES = Object.fromEntries(cities.map(c => [c.code, c.name]));
        populateSelects(cities);
    } catch (err) {
        setStatusFor($('status'), err.message, 'error');
    }

    $('search-form').addEventListener('submit', onSearchSubmit);
    $('calendar-form').addEventListener('submit', onCalendarSubmit);
    $('popular-form').addEventListener('submit', onPopularSubmit);
}

init();