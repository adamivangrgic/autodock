async function apiCall(url, context) {
    try {
        const response = await fetch(url, {
            method: "POST",
            body: JSON.stringify(context),
            headers: {
                "Content-type": "application/json; charset=UTF-8"
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        return data;

    } catch (err) {
        console.error('API call failed:', err);
        // throw err;
        return err;
    }
}

async function apiAction(url, context){
    document.querySelector('.loader').style.opacity = 1; 
    const msg = await apiCall(url, context);
    window.location.reload();
}

//

function humanizeDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffInMs = date - now;
    const diffInDays = Math.round(diffInMs / (1000 * 60 * 60 * 24));
    const diffInHours = Math.round(diffInMs / (1000 * 60 * 60));
    const diffInMinutes = Math.round(diffInMs / (1000 * 60));

    const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });

    if (Math.abs(diffInMinutes) < 60) {
        return rtf.format(diffInMinutes, 'minute');
    } else if (Math.abs(diffInHours) < 24) {
        return rtf.format(diffInHours, 'hour');
    } else {
        return rtf.format(diffInDays, 'day');
    }
}

async function fill_log_output(url, context, box_selector){
    const element = document.querySelector(box_selector);
    const isNearBottom = element.scrollHeight - element.scrollTop - element.clientHeight < 50;

    try {
        const result = await apiCall(url, context);
        element.textContent = result;
    } catch (error) {
        element.textContent = 'Error: ' + error.message;
    }

    if (isNearBottom) {
        element.scrollTop = element.scrollHeight;
    }
}

// 

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('[data-date]').forEach(element => {
        const humanized = humanizeDate(element.getAttribute('data-date'));
        element.textContent = humanized;
    });
});