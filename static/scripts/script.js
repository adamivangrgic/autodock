function apiCall(url, context){
    fetch(url, {
        method: "POST",
        body: JSON.stringify(context),
        headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    });

}