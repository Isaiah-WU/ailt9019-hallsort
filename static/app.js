let providerName='the configured model provider';
let latestCheckId = 0;
let serverInfo = null;

const KEY_STORE='hallsort.key', PROV_STORE='hallsort.provider';
function loadKey(){
  try{ return {provider: sessionStorage.getItem(PROV_STORE)||'openrouter', key: (sessionStorage.getItem(KEY_STORE)||'').trim()} }
  catch(e){ return {provider:'openrouter', key:''} }
}
function authHeaders(){
  const k=loadKey();
  return k.key ? {'X-Provider':k.provider,'X-Provider-Key':k.key} : {};
}
function providerLabel(id){
  const p = serverInfo && serverInfo.providers && serverInfo.providers.find(x=>x.id===id);
  return p ? p.label : id;
}
function refreshModeLabel(){
  if(!serverInfo) return;
  const k=loadKey();
  if(k.key){ mode.options[1].textContent='AI interpretation · your '+providerLabel(k.provider)+' key'; return }
  mode.options[1].textContent = serverInfo.llm_available
    ? 'AI interpretation · '+serverInfo.provider+' / '+serverInfo.model
    : 'AI interpretation · add your own key, or use catalog';
}
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
    serverInfo = data;
    providerName = data.provider;
    document.querySelector('#version').textContent = 'Rules ' + data.rule_version;
    refreshModeLabel();
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
            headers: {'Content-Type': 'application/json', ...authHeaders()},
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


/* --- Photo to draft description, and optional bring-your-own-key --- */

const photoInput = document.querySelector('#photo');
const describeBtn = document.querySelector('#describe');
const dropBtn = document.querySelector('#drop-photo');
const photoStatus = document.querySelector('#photo-status');
const preview = document.querySelector('#photo-preview');
const keyPanel = document.querySelector('#key-panel');
const keyProvider = document.querySelector('#key-provider');
const keyValue = document.querySelector('#key-value');
const keyClear = document.querySelector('#key-clear');

let photo = null;

function setPhotoStatus(text) {
    photoStatus.textContent = text || '';
}

function shrink(file, max) {
    max = max || 1024;
    return new Promise((resolve, reject) => {
        const img = new Image();
        const url = URL.createObjectURL(file);
        img.onload = () => {
            const scale = Math.min(1, max / Math.max(img.width, img.height));
            const w = Math.max(1, Math.round(img.width * scale));
            const h = Math.max(1, Math.round(img.height * scale));
            const canvas = document.createElement('canvas');
            canvas.width = w;
            canvas.height = h;
            canvas.getContext('2d').drawImage(img, 0, 0, w, h);
            URL.revokeObjectURL(url);
            const data = canvas.toDataURL('image/jpeg', 0.85);
            resolve({b64: data.split(',')[1], mime: 'image/jpeg'});
        };
        img.onerror = () => {
            URL.revokeObjectURL(url);
            reject(new Error('Could not read that image.'));
        };
        img.src = url;
    });
}

function resetPhoto() {
    photo = null;
    photoInput.value = '';
    preview.hidden = true;
    preview.removeAttribute('src');
    describeBtn.disabled = true;
    dropBtn.hidden = true;
}

if (photoInput) {
    photoInput.addEventListener('change', async () => {
        const file = photoInput.files && photoInput.files[0];
        if (!file) return;
        if (['image/jpeg', 'image/png', 'image/webp'].indexOf(file.type) === -1) {
            setPhotoStatus('Use a JPEG, PNG or WebP image.');
            resetPhoto();
            return;
        }
        if (file.size > 12 * 1024 * 1024) {
            setPhotoStatus('That image is larger than 12 MB. Use a smaller one.');
            resetPhoto();
            return;
        }
        try {
            photo = await shrink(file);
        } catch (error) {
            setPhotoStatus(error.message);
            resetPhoto();
            return;
        }
        preview.src = 'data:' + photo.mime + ';base64,' + photo.b64;
        preview.hidden = false;
        describeBtn.disabled = false;
        dropBtn.hidden = false;
        setPhotoStatus('Photo ready. Describe it, then check the wording before you submit.');
    });

    describeBtn.addEventListener('click', async () => {
        if (!photo) return;
        describeBtn.disabled = true;
        setPhotoStatus('Reading the photo…');
        try {
            const response = await fetch('/api/describe', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', ...authHeaders()},
                body: JSON.stringify({image: photo.b64, mime: photo.mime})
            });
            const data = await response.json();
            if (data.status === 'described') {
                input.value = data.description.slice(0, 400);
                input.dispatchEvent(new Event('input', {bubbles: true}));
                input.focus();
                const unsure = /unclear|not sure|unknown|cannot tell/i.test(data.description);
                setPhotoStatus(unsure
                    ? 'The photo did not show whether it is clean. Add "clean" or "soiled", then find the category.'
                    : 'Check and edit the wording, then find the category. No bin is assigned from a photo.');
            } else {
                setPhotoStatus(data.message || 'That photo could not be described.');
            }
        } catch (error) {
            setPhotoStatus('Could not reach the server.');
        } finally {
            describeBtn.disabled = false;
        }
    });

    dropBtn.addEventListener('click', () => {
        resetPhoto();
        setPhotoStatus('');
    });
}

if (keyPanel) {
    const saved = loadKey();
    keyProvider.value = saved.provider;
    keyValue.value = saved.key;
    if (saved.key) keyPanel.open = true;

    const persist = () => {
        try {
            sessionStorage.setItem(PROV_STORE, keyProvider.value);
            sessionStorage.setItem(KEY_STORE, keyValue.value.trim());
        } catch (error) { /* private mode, ignore */ }
        refreshModeLabel();
    };

    keyValue.addEventListener('input', persist);
    keyProvider.addEventListener('change', persist);
    keyClear.addEventListener('click', () => {
        keyValue.value = '';
        try { sessionStorage.removeItem(KEY_STORE); } catch (error) {}
        refreshModeLabel();
        keyValue.focus();
    });
}
