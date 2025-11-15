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
        throw err;
    }
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

    const scrollTopBefore = element.scrollTop;
    const clientHeight = element.clientHeight;

    try {
        const result = await apiCall(url, context);
        
        const topChild = getChildAtScrollPosition(element, scrollTopBefore);
        
        element.textContent = result;
        
        if (topChild && element.contains(topChild)) {
            topChild.scrollIntoView({ block: 'start' });
        } else {
            element.scrollTop = scrollTopBefore;
        }
    } catch (error) {
        element.textContent = 'Error: ' + error.message;
        element.scrollTop = scrollTopBefore;
    }

    function getChildAtScrollPosition(container, scrollTop) {
        const children = container.children;
        for (let i = 0; i < children.length; i++) {
            const child = children[i];
            const offsetTop = child.offsetTop;
            const height = child.offsetHeight;
            
            if (scrollTop >= offsetTop && scrollTop < offsetTop + height) {
                return child;
            }
        }
        return children[0] || null;
    }
}

// 

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('[data-date]').forEach(element => {
        const humanized = humanizeDate(element.getAttribute('data-date'));
        element.textContent = humanized;
    });
});