import { requestProvider } from "/webln/lib/client";
const user_websocket = new WebSocket("{{ WEBSOCKET_HOST }}");
const user_id = "{{ session['user_id'] }}";
document.addEventListener('DOMContentLoaded', async function () {
    user_websocket.onopen = function (event) {
        const user_id_object = {
            user_id: user_id,
            action: 'open'
        };
        const user_id_string = JSON.stringify(user_id_object);
        user_websocket.send(user_id_string);
    };
    user_websocket.onmessage = function (event) {
        console.log(event.data);
    };

    function connectFormSubmit(event) {
        event.preventDefault();
        const form_data = $(this).serialize();
        console.log(form_data);
        user_websocket.send(form_data)
    }

    const connectForm = document.getElementById('connect_form');
    connectForm.onsubmit = connectFormSubmit;


    let webln;
    try {
        webln = await requestProvider();
    } catch (err) {
        console.log(err);
        // Handle users without WebLN
    }

// Elsewhere in the code...
    if (webln) {
        webln.enable();
        // Call webln functions
    }


}, false);

