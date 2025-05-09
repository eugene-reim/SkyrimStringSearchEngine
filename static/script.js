// Упрощенная функция debounce для оптимизации запросов
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// Переменные для пагинации
let currentOffset = 0;
let isLoading = false;
let hasMore = true;
let currentQuery = '';

// Функция для выполнения поиска
let abortController = null;

async function performSearch(query, loadMore = false) {
    if (!loadMore) {
        currentOffset = 0;
        hasMore = true;
        currentQuery = query;
        document.getElementById('results').innerHTML = '';
    }

    if (!query || isLoading || !hasMore) return;
    if (!query) {
        document.getElementById('results').innerHTML = '';
        return;
    }

    // Отменяем предыдущий запрос, если он существует
    if (abortController && !abortController.signal.aborted) {
        abortController.abort();
    }
    abortController = new AbortController();
    
    // Добавляем обработчик для очистки при размонтировании
    window.addEventListener('beforeunload', () => {
        if (abortController && !abortController.signal.aborted) {
            abortController.abort();
        }
    });

    isLoading = true;
    try {
        const response = await fetch(
            `/api/v1/search?query=${encodeURIComponent(query)}&case_insensitive=true&offset=${currentOffset}&limit=20`,
            { signal: abortController.signal }
        );
        console.log('Response status:', response.status);
        const data = await response.json();
        console.log('API response:', data);
        
        // Обновляем статистику с проверкой элементов
        const matchesEl = document.getElementById('matches-count');
        const totalEl = document.getElementById('total-count');
        
        if (matchesEl && totalEl && data.stats) {
            matchesEl.textContent = data.stats.matches;
            totalEl.textContent = data.stats.total;
            console.log('Updated stats:', data.stats.matches, data.stats.total);
        } else {
            console.error('Failed to update stats - elements:', 
                !!matchesEl, 
                !!totalEl,
                'data:', data.stats
            );
        }
        
        const resultsDiv = document.getElementById('results');
        if (!loadMore) {
            resultsDiv.innerHTML = '';
        }

        if (data.results.length > 0) {
            hasMore = data.results.length >= 20;
                // Шаблон для элемента результата
                const resultTemplate = () => `
                    <div class="result-item">
                        <h3 class="result-item-plugin-name">%plugin-name%</h3>
                        <div class="result-row">
                            <span class="result-label">Оригинал:</span>
                            <code class="result-code result-original">
                                 %original-text%
                            </code>
                            <span class="copy-icon" onclick="copyToClipboard(this)">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                                </svg>
                            </span>
                        </div>
                        <div class="result-row">
                            <span class="result-label">Перевод: </span>
                            <code class="result-code result-translated">
                                %translated-text%
                            </code>
                            <span class="copy-icon" onclick="copyToClipboard(this)">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                                </svg>
                            </span>
                        </div>
                    </div>
                `;

                data.results.forEach(result => {
                    const original = result.original_string || '';
                    const translated = result.translated_string || '';
                    const template = document.createElement('template');
                    template.innerHTML = resultTemplate();
                    const item = template.content.cloneNode(true);
                    
                    // Используем querySelector вместо getElementsByClassName
                    item.querySelector('.result-original').textContent = JSON.stringify(original).slice(1, -1);
                    item.querySelector('.result-translated').textContent = JSON.stringify(translated).slice(1, -1);
                    item.querySelector('.result-item-plugin-name').textContent = result.plugin_name;
                    
                    
                    resultsDiv.appendChild(item);
                    
            });
        } else {
            resultsDiv.innerHTML = '<p>Ничего не найдено</p>';
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            // Запрос был отменен, это нормально
            return;
        }
        console.error('Ошибка при поиске:', error);
        document.getElementById('results').innerHTML = '<p>Произошла ошибка при поиске</p>';
    } finally {
        isLoading = false;
        abortController = null;
    }
}

// Флаг для отслеживания активного запроса
let isSearching = false;

// Оптимизированный обработчик ввода с debounce
const optimizedSearch = debounce(async (query) => {
    if (isSearching) {
        if (abortController) {
            abortController.abort();
        }
    }
    
    isSearching = true;
    try {
        await performSearch(query);
    } finally {
        isSearching = false;
    }
}, 500);

// Обработчик ввода в поле поиска
document.getElementById('searchQuery').addEventListener('input', (e) => {
    try {
        optimizedSearch(e.target.value);
    } catch (error) {
        if (error.name !== 'AbortError') {
            console.error('Ошибка при обработке ввода:', error);
        }
    }
});


// Функция для копирования текста в буфер обмена
function copyToClipboard(copyIcon) {
    // Получаем текст из предыдущего элемента
    const textElement = copyIcon.previousElementSibling;
    const text = textElement.textContent;
    navigator.clipboard.writeText(text)
        .then(() => {
            // Показать уведомление об успешном копировании
            const notification = document.createElement('div');
            notification.className = 'copy-notification';
            notification.textContent = 'Скопировано!';
            document.body.appendChild(notification);
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 2000);
        })
        .catch(err => {
            if (err.name !== 'AbortError') {
                console.error('Ошибка при копировании:', err);
            }
        });
}

// Обработчик отправки формы (для поддержки Enter)
document.getElementById('searchForm').addEventListener('submit', (e) => {
    e.preventDefault();
    try {
        performSearch(document.getElementById('searchQuery').value);
    } catch (error) {
        if (error.name !== 'AbortError') {
            console.error('Ошибка при отправке формы:', error);
        }
    }
});

// Обработчик бесконечной прокрутки
window.addEventListener('scroll', () => {
    const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
    
    if (scrollTop + clientHeight >= scrollHeight - 100 && !isLoading && hasMore) {
        currentOffset += 20;
        performSearch(currentQuery, true);
    }
});
