async function apiCall(url, context){
    const response = await fetch(url, {
        method: "POST",
        body: JSON.stringify(context),
        headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    });

    return response;
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

function fill_log_output(url, context){
    const element = document.querySelector('#log-output');
    element.textContent = apiCall(url, context);
}

// 

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('[data-date]').forEach(element => {
        const humanized = humanizeDate(element.getAttribute('data-date'));
        element.textContent = humanized;
    });

    document.querySelectorAll('#log-output').forEach(element => {
        element.scrollTop = element.scrollHeight;
    });
});