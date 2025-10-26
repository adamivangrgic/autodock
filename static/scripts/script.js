function apiCall(url, context){
    fetch(url, {
        method: "POST",
        body: context,
        headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    });

}