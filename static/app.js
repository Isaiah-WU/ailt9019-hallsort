let providerName='the configured model provider';
let latestCheckId = 0;
const form=document.querySelector('#check-form'), input=document.querySelector('#item'), mode=document.querySelector('#mode'), results=document.querySelector('#results'), submit=document.querySelector('#submit');
function el(tag,text,cls){const n=document.createElement(tag);n.textContent=text;if(cls)n.className=cls;return n}
document.querySelectorAll('[data-query]').forEach(button => {
    button.addEventListener('click', () => {
        input.value = button.dataset.query;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.focus();
    });
});
function updateModeNote() {
    document.querySelector('#mode-note').textContent = mode.value === 'catalog'
        ? 'Catalog mode matches listed names exactly. Join separate items with +.'
        : 'AI mode sends your item description to ' + providerName + '. Avoid personal information.';
}
mode.addEventListener('change', updateModeNote);
fetch('/api/info').then(response => response.json()).then(data => {
    providerName = data.provider;
    document.querySelector('#version').textContent = 'Rules ' + data.rule_version;
    mode.options[1].textContent = data.llm_available
        ? 'AI interpretation · ' + data.provider + ' / ' + data.model
        : 'AI interpretation · not configured yet';
    updateModeNote();
    data.examples.forEach(example => document.querySelector('#catalog').append(el('li', example)));
}).catch(() => {
    document.querySelector('#version').textContent = 'Server unavailable';
});

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Give each request a unique ID.
    const checkId = ++latestCheckId;

    // Save the input at submission time.
    const query = input.value;
    const searchMode = mode.value;

    submit.disabled = true;
    submit.textContent = 'Checking…';

    results.replaceChildren(
        el('p', 'Checking the item and its source…')
    );

    try {
        const response = await fetch('/api/classify', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                query: query,
                mode: searchMode
            })
        });

        if (!response.ok) {
            throw new Error('Invalid request');
        }

        const data = await response.json();

        // Ignore outdated responses.
        if (checkId !== latestCheckId) {
            return;
        }

        // Determine the appropriate result heading.
        let heading;

        if (data.status === 'classified') {
            if (data.parts.every(p => p.bin === 'Not accepted')) {
                heading = 'Not accepted by this guide.';
            } else if (data.parts.some(p => p.bin === 'Not accepted')) {
                heading = 'Some parts are not accepted by this guide.';
            } else {
                heading = 'Here is how to separate it.';
            }
        } else if (data.status === 'unavailable') {
            heading = 'This mode is unavailable.';
        } else {
            heading = 'Let’s check before guessing.';
        }

        let sourceLabel = 'VERIFIED CATALOG · NO MODEL CALL';
        if (data.mode === 'llm') {
            if (!data.model_attempted) {
                sourceLabel = 'LOCAL CHECK · NO MODEL CALL';
            } else if (data.status === 'unavailable') {
                sourceLabel = 'PROVIDER REQUEST · NO VERIFIED ANSWER';
            } else {
                sourceLabel = 'AI INTERPRETATION';
            }
        }
        results.replaceChildren(
            el('p', sourceLabel, 'result-mode'),
            el('h2', heading, 'result-title'),
            el('p', data.message, 'result-msg')
        );

        // Display classified items.
        data.parts.forEach(p => {
            const card = el('article', '', 'part');

            card.append(
                el('h3', p.part),
                el('span', p.bin, 'bin'),
                el('p', p.reason)
            );

            const a = el(
                'a',
                p.rule_id + ' · ' + p.source_title + ' ↗'
            );

            a.href = p.source;
            a.target = '_blank';
            a.rel = 'noopener';

            card.append(a);
            results.append(card);
        });

        results.append(
            el('p', data.notice, 'fine')
        );

    } catch (error) {
        if (checkId === latestCheckId) {
            results.replaceChildren(
                el('h2',
                    'We could not complete the check.',
                    'result-title'
                ),
                el('p',
                    'Check that the local server is running, then try again.'
                )
            );
        }

    } finally {
        // Only the latest request can update button state.
        if (checkId === latestCheckId) {
            submit.disabled = false;

            submit.replaceChildren(
                document.createTextNode('Find the right category '),
                el('span', '→')
            );
        }
    }
});



function showReadyState() {
  const empty = el('div', '', 'empty');

  empty.append(
    el('span', '02 / YOUR RESULT'),
    el('h2', 'Ready for a new check.'),
    el('p', 'Click "Find the right category" to check the current input.')
  );

  results.replaceChildren(empty);
}

input.addEventListener('input', showReadyState);

mode.addEventListener('change', showReadyState);



document.querySelector('#clear-input').addEventListener('click', () => {
    input.value = '';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.focus();
});


function invalidatePendingCheck() {
  latestCheckId++;

  submit.disabled = false;
  submit.replaceChildren(
    document.createTextNode('Find the right category '),
    el('span', '→')
  );
}

input.addEventListener('input', invalidatePendingCheck);
mode.addEventListener('change', invalidatePendingCheck);



const inputFeedback = document.querySelector('#input-feedback');
function updateInputFeedback() {
  if (inputFeedback) inputFeedback.textContent = `${input.value.length} / 400 characters`;
}
input.addEventListener('input', updateInputFeedback);
updateInputFeedback();
