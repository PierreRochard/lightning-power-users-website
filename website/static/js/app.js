
document.addEventListener('DOMContentLoaded', async function () {

    let selectedCapacity;
    let selectedCapacityText;
    let selectedCapacityFeeRate;
    let selectedTransactionFeeRate;

    const capacitySelect = document.querySelector('select[name="capacity"]');
    const capacityFeeRateSelect = document.querySelector('select[name="capacity_fee_rate"]');
    const transactionFeeRateSelect = document.querySelector('select[name="transaction_fee_rate"]');
    capacitySelect.onchange = changeEventHandler;
    transactionFeeRateSelect.onchange = changeEventHandler;
    capacityFeeRateSelect.onchange = changeEventHandler;
    changeEventHandler();


    function changeEventHandler() {
        const capacitySelect = document.querySelector('select[name="capacity"]');
        const capacityFeeRateSelect = document.querySelector('select[name="capacity_fee_rate"]');
        const transactionFeeRateSelect = document.querySelector('select[name="transaction_fee_rate"]');

        selectedCapacity = parseInt(capacitySelect.selectedOptions[0].value);
        selectedCapacityText = capacitySelect.selectedOptions[0].textContent;
        const selectedCapacityUsd = Math.round(selectedCapacity * pricePerSat * 100) / 100;
        if (selectedCapacityText.startsWith('Reciprocate')) {
            capacityFeeRateSelect.options[0].disabled = false;
            capacityFeeRateSelect.value = 0;
            capacityFeeRateSelect.disabled = true;
            document.querySelector('#selected-capacity').innerHTML = '-';
            document.querySelector('#selected-capacity-usd').innerHTML = '-';
        } else {
            capacityFeeRateSelect.disabled = false;
            console.log(capacityFeeRateSelect.value);
            if (Math.round(capacityFeeRateSelect.value * 100) === 0) {
                capacityFeeRateSelect.value = 0.005;
            }
            capacityFeeRateSelect.options[0].disabled = true;
            document.querySelector('#selected-capacity').innerHTML = selectedCapacity.toLocaleString();
            document.querySelector('#selected-capacity-usd').innerHTML = selectedCapacityUsd.toLocaleString(undefined, {
                maximumFractionDigits: 2,
                minimumFractionDigits: 2
            });
        }

        selectedCapacityFeeRate = parseFloat(capacityFeeRateSelect.selectedOptions[0].value);
        document.querySelector('#capacity-fee-rate').innerHTML = selectedCapacityFeeRate.toLocaleString(undefined, {style: 'percent', maximumFractionDigits: 1});
        document.querySelector('#capacity-fee-rate-usd').innerHTML = selectedCapacityFeeRate.toLocaleString(undefined, {style: 'percent', maximumFractionDigits: 1});

        const capacityFee = Math.round(selectedCapacity * selectedCapacityFeeRate);
        const capacityFeeUsd = Math.round(capacityFee * pricePerSat * 100) / 100;
        if (capacityFee > 0) {
            document.querySelector('#capacity-fee').innerHTML = capacityFee.toLocaleString();
            document.querySelector('#capacity-fee-usd').innerHTML = capacityFeeUsd.toLocaleString(undefined, {
                maximumFractionDigits: 2,
                minimumFractionDigits: 2
            });

            document.querySelector('#capacity-fee-payment').innerHTML = capacityFee.toLocaleString();
            document.querySelector('#capacity-fee-usd-payment').innerHTML = capacityFeeUsd.toLocaleString(undefined, {
                maximumFractionDigits: 2,
                minimumFractionDigits: 2
            });
        } else {
            document.querySelector('#capacity-fee-payment').innerHTML = '-';
            document.querySelector('#capacity-fee-usd-payment').innerHTML = '-';
        }

        selectedTransactionFeeRate = parseInt(transactionFeeRateSelect.selectedOptions[0].value);
        document.querySelector('#transaction-fee-rate').innerHTML = selectedTransactionFeeRate.toLocaleString();

        const expectedBytes = parseInt(document.querySelector('#expected-bytes').innerHTML);
        const transactionFee = selectedTransactionFeeRate * expectedBytes;
        const transactionFeeUsd = Math.round(transactionFee * pricePerSat * 100) / 100;
        document.querySelector('#transaction-fee').innerHTML = transactionFee.toLocaleString();
        document.querySelector('#transaction-fee-usd').innerHTML = transactionFeeUsd.toLocaleString(undefined, {
            maximumFractionDigits: 2,
            minimumFractionDigits: 2
        });

        document.querySelector('#transaction-fee-payment').innerHTML = transactionFee.toLocaleString();
        document.querySelector('#transaction-fee-usd-payment').innerHTML = transactionFeeUsd.toLocaleString(undefined, {
            maximumFractionDigits: 2,
            minimumFractionDigits: 2
        });

        const totalFee = transactionFee + capacityFee;
        const totalFeeUsd = Math.round(totalFee * pricePerSat * 100) / 100;
        document.querySelector('#total-fee').innerHTML = totalFee.toLocaleString();
        document.querySelector('#total-fee-usd').innerHTML = totalFeeUsd.toLocaleString(undefined, {
            maximumFractionDigits: 2,
            minimumFractionDigits: 2
        });
    }

    const connectForm = document.getElementById('connect_form');
    const connectButton = document.getElementById('connect_button');
    const connectTextarea = document.getElementById('connect_textarea');
    const progressBar = document.getElementById('progress-bar');
    const progressBarDiv = document.getElementById('progress-bar-div');

    const errorMessage = document.getElementById('error_message');

    const connectTab = document.getElementById('connect-tab');
    const connectTabContent = document.getElementById('connect-tab-content');

    const capacityTab = document.getElementById('capacity-tab');
    const capacityTabContent = document.getElementById('capacity-tab-content');

    const chainTab = document.getElementById('chain-tab');
    const chainTabContent = document.getElementById('chain-tab-content');

    const paymentTab = document.getElementById('payment-tab');
    const paymentTabContent = document.getElementById('payment-tab-content');

    const qrCodeDiv = document.getElementById('qrcode-div');
    const payWithJoule = document.getElementById('pay-with-joule');
    const payreqInput = document.getElementById('payreq-input');

    const paymentInfo = document.getElementById('payment-info');

    function websocketSend(data) {
        const data_string = JSON.stringify(data);
        session_websocket.send(data_string);
        console.log(data_string);
    }

    function showProgressBar(content) {
        progressBar.style.width = "100%";
        progressBar.textContent = content;
        progressBarDiv.style.visibility = "visible";
    }

    function hideProgressBar() {
        progressBarDiv.style.visibility = "hidden";
    }

    function hideErrorMessage() {
        errorMessage.textContent = "";
        errorMessage.style.visibility = "hidden";
    }

    session_websocket.onopen = function (event) {
        const session_id_object = {
            session_id: session_id,
            action: "register"
        };

        websocketSend(session_id_object);
    };

    session_websocket.onmessage = function (event) {
        const msg = JSON.parse(event.data);
        switch(msg.action) {
            case "registered":
                console.log("registered");
                document.onkeydown = null;
                document.onkeydown = function(event) {
                    if (event.which === 13 || event.which === 9) {
                        connectForm.dispatchEvent(new Event("submit", {cancelable: true}));
                        event.preventDefault();
                    }
                };
                connectTextarea.focus();
                break;
            case "connected":
                console.log("connected");
                if (msg.data === null) {
                    capacitySelect.options[0].disabled = true;
                    capacitySelect.value = 500000;
                    changeEventHandler();
                } else {
                    const reciprocateAmount = parseInt(msg.data.capacity);
                    const reciprocateAmountString = reciprocateAmount.toLocaleString();
                    capacitySelect.options[0].value = reciprocateAmount;
                    capacitySelect.options[0].textContent = 'Reciprocate ' + reciprocateAmountString;
                }
                hideProgressBar();
                connectTabContent.classList.remove('show');
                connectTabContent.classList.remove('active');
                connectTab.classList.remove('active');
                connectTab.classList.add('disabled');
                capacityTab.classList.remove('disabled');
                capacityTab.classList.add('active');
                $('#capacity-tab-content').tab('show');
                document.onkeydown = null;
                document.onkeydown = function(event) {
                    if (event.which === 13 || event.which === 9) {
                        capacityForm.dispatchEvent(new Event("submit", {cancelable: true}));
                        event.preventDefault();
                    }
                };
                break;
            case "confirmed_capacity":
                console.log("capacity_confirmed");
                hideProgressBar();
                capacityTabContent.classList.remove('show');
                capacityTabContent.classList.remove('active');
                capacityTab.classList.remove('active');
                capacityTab.classList.add('disabled');
                chainTab.classList.remove('disabled');
                chainTab.classList.add('active');
                $('#chain-tab-content').tab('show');
                document.onkeydown = null;
                document.onkeydown = function(event) {
                    if (event.which === 13 || event.which === 9) {
                        chainForm.dispatchEvent(new Event("submit", {cancelable: true}));
                        event.preventDefault();
                    }
                };
                break;
            case "payment_request":
                console.log("confirmed_chain_fee");
                hideProgressBar();

                const image = document.getElementById("qrcode");
                image.src = msg.qrcode;
                qrCodeDiv.appendChild(image);

                payWithJoule.href = msg.uri;
                payreqInput.value = msg.payment_request;

                chainTabContent.classList.remove('show');
                chainTabContent.classList.remove('active');
                chainTab.classList.remove('active');
                chainTab.classList.add('disabled');
                paymentTab.classList.remove('disabled');
                paymentTab.classList.add('active');
                $('#payment-tab-content').tab('show');
                document.onkeydown = null;
                document.onkeydown = function(event) {
                    if (event.which === 13 || event.which === 9) {
                        payWithJoule.click();
                        event.preventDefault();
                    }
                };
                break;
            case "receive_payment":
                console.log(event.data);
                document.onkeydown = null;
                paymentInfo.className += paymentInfo.className ? ' paid' : 'paid';
                showProgressBar("Opening channel...");
                break;
            case "channel_open":
                console.log(event.data);
                hideProgressBar();
                break;
            case "error_message":
                console.log("error message");
                document.onkeydown = null;
                hideProgressBar();
                errorMessage.style.visibility = "visible";
                errorMessage.textContent = msg.error;
                connectButton.disabled = false;
                connectTextarea.disabled = false;
                break;
        }
    };

    function connectFormSubmit(event) {
        event.preventDefault();
        showProgressBar("Connecting...");
        const formData = JSON.parse(JSON.stringify(jQuery('#connect_form').serializeArray()));
        connectButton.disabled = true;
        connectTextarea.disabled = true;

        hideErrorMessage();

        const connectFormDataObject = {
            session_id: session_id,
            action: 'connect',
            form_data: formData
        };
        websocketSend(connectFormDataObject);
    }
    connectForm.onsubmit = connectFormSubmit;

    const capacityForm = document.getElementById('capacity_form');
    const capacityButton = document.getElementById('capacity_button');

    function capacityFormSubmit(event) {
        event.preventDefault();
        showProgressBar("Confirming capacity...");
        const formData = JSON.parse(JSON.stringify(jQuery('#capacity_form').serializeArray()));
        capacityButton.disabled = true;

        hideErrorMessage();

        const capacityFormDataObject = {
            session_id: session_id,
            action: 'capacity_request',
            form_data: formData
        };
        websocketSend(capacityFormDataObject);
    }
    capacityForm.onsubmit = capacityFormSubmit;


    const chainForm = document.getElementById('chain_form');
    const chainButton = document.getElementById('chain_button');

    function chainFormSubmit(event) {
        event.preventDefault();
        showProgressBar("Confirming chain fee...");
        const formData = JSON.parse(JSON.stringify(jQuery('#chain_form').serializeArray()));
        chainButton.disabled = true;

        hideErrorMessage();

        const chainFormDataObject = {
            session_id: session_id,
            action: 'chain_fee',
            form_data: formData
        };
        websocketSend(chainFormDataObject);
    }
    chainForm.onsubmit = chainFormSubmit;

}, false);

