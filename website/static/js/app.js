
document.addEventListener('DOMContentLoaded', async function () {

    const connectForm = document.getElementById('connect_form');
    const connectButton = document.getElementById('connect_button');
    const connectTextarea = document.getElementById('connect_textarea');
    const progressBar = document.getElementById('progress_bar');
    const connectError = document.getElementById('connect_error');

    function websocketSend(data) {
        const data_string = JSON.stringify(data);
        user_websocket.send(data_string);
    }

    user_websocket.onopen = function (event) {
        const user_id_object = {
            user_id: user_id,
            action: "register"
        };
        websocketSend(user_id_object);
    };

    user_websocket.onmessage = function (event) {
        console.log(event.data);
        const msg = JSON.parse(event.data);
        switch(msg.action) {
            case "registered":
                console.log("registered");
                break;
            case "connected":
                console.log("connected");
                progressBar.style.width = "100%";
                progressBar.textContent = "";
                break;
            case "connect_error":
                console.log("connect error");
                progressBar.style.width = "0%";
                progressBar.textContent = "";
                connectError.style.visibility = "visible";
                connectError.textContent = msg.error;
                connectButton.disabled = false;
                connectTextarea.disabled = false;

        }
    };

    function connectFormSubmit(event) {
        event.preventDefault();
        progressBar.style.width = "50%";
        progressBar.textContent = "Connecting...";
        const formData = JSON.parse(JSON.stringify(jQuery('#connect_form').serializeArray()));
        connectButton.disabled = true;
        connectTextarea.disabled = true;

        connectError.textContent = "";
        connectError.style.visibility = "hidden";

        const connectFormDataObject = {
            user_id: user_id,
            action: 'connect',
            form_data: formData
        };
        websocketSend(connectFormDataObject);
    }
    connectForm.onsubmit = connectFormSubmit;


}, false);

