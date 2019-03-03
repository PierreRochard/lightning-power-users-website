
document.addEventListener('DOMContentLoaded', async function () {

    let selectedCapacity;
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
        const selectedCapacityUsd = Math.round(selectedCapacity * pricePerSat * 100) / 100;
        if (selectedCapacity > 0) {
            capacityFeeRateSelect.disabled = false;
            console.log(capacityFeeRateSelect.value);
            if (Math.round(capacityFeeRateSelect.value * 100) === 0) {
                capacityFeeRateSelect.value = 0.03;
            }
            capacityFeeRateSelect.options[0].disabled = true;
            document.querySelector('#selected-capacity').innerHTML = selectedCapacity.toLocaleString();
            document.querySelector('#selected-capacity-usd').innerHTML = selectedCapacityUsd.toLocaleString(undefined, {
                maximumFractionDigits: 2,
                minimumFractionDigits: 2
            });
        } else {
            capacityFeeRateSelect.options[0].disabled = false;
            capacityFeeRateSelect.value = 0;
            capacityFeeRateSelect.disabled = true;
            document.querySelector('#selected-capacity').innerHTML = '-';
            document.querySelector('#selected-capacity-usd').innerHTML = '-';
        }

        selectedCapacityFeeRate = parseFloat(capacityFeeRateSelect.selectedOptions[0].value);
        document.querySelector('#capacity-fee-rate').innerHTML = selectedCapacityFeeRate.toLocaleString(undefined, {style: 'percent'});
        document.querySelector('#capacity-fee-rate-usd').innerHTML = selectedCapacityFeeRate.toLocaleString(undefined, {style: 'percent'});

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
    const progressBar = document.getElementById('progress_bar');

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
    const payreqInput = document.getElementById('payreq-input');

    const paymentInfo = document.getElementById('payment-info');

    function websocketSend(data) {
        const data_string = JSON.stringify(data);
        session_websocket.send(data_string);
        console.log(data_string);
    }

    session_websocket.onopen = function (event) {
        const session_id_object = {
            session_id: session_id,
            action: "register"
        };

        websocketSend(session_id_object);
    };

    session_websocket.onmessage = function (event) {
        console.log(event.data);
        const msg = JSON.parse(event.data);
        switch(msg.action) {
            case "registered":
                console.log("registered");
                break;
            case "connected":
                console.log("connected");
                progressBar.style.width = "0%";
                progressBar.textContent = "";
                connectTabContent.classList.remove('show');
                connectTabContent.classList.remove('active');
                connectTab.classList.remove('active');
                connectTab.classList.add('disabled');
                capacityTab.classList.remove('disabled');
                capacityTab.classList.add('active');
                $('#capacity-tab-content').tab('show');
                break;
            case "confirmed_capacity":
                console.log("capacity_confirmed");
                progressBar.style.width = "0%";
                progressBar.textContent = "";
                capacityTabContent.classList.remove('show');
                capacityTabContent.classList.remove('active');
                capacityTab.classList.remove('active');
                capacityTab.classList.add('disabled');
                chainTab.classList.remove('disabled');
                chainTab.classList.add('active');
                $('#chain-tab-content').tab('show');
                break;
            case "payment_request":
                console.log("confirmed_chain_fee");
                progressBar.style.width = "0%";
                progressBar.textContent = "";

                const image = document.getElementById("qrcode");
                image.src = msg.qrcode;
                qrCodeDiv.appendChild(image);

                payreqInput.value = msg.payment_request;

                chainTabContent.classList.remove('show');
                chainTabContent.classList.remove('active');
                chainTab.classList.remove('active');
                chainTab.classList.add('disabled');
                paymentTab.classList.remove('disabled');
                paymentTab.classList.add('active');
                $('#payment-tab-content').tab('show');
                break;
            case "payment_received":
                console.log(event.data);
                paymentInfo.className += paymentInfo.className ? ' paid' : 'paid';
                break;
            case "error_message":
                console.log("error message");
                progressBar.style.width = "0%";
                progressBar.textContent = "";
                errorMessage.style.visibility = "visible";
                errorMessage.textContent = msg.error;
                connectButton.disabled = false;
                connectTextarea.disabled = false;
                break;
        }
    };

    function connectFormSubmit(event) {
        event.preventDefault();
        progressBar.style.width = "50%";
        progressBar.textContent = "Connecting...";
        const formData = JSON.parse(JSON.stringify(jQuery('#connect_form').serializeArray()));
        connectButton.disabled = true;
        connectTextarea.disabled = true;

        errorMessage.textContent = "";
        errorMessage.style.visibility = "hidden";

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
        progressBar.style.width = "50%";
        progressBar.textContent = "Confirming capacity...";
        const formData = JSON.parse(JSON.stringify(jQuery('#capacity_form').serializeArray()));
        capacityButton.disabled = true;

        errorMessage.textContent = "";
        errorMessage.style.visibility = "hidden";

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
        progressBar.style.width = "50%";
        progressBar.textContent = "Confirming chain fee...";
        const formData = JSON.parse(JSON.stringify(jQuery('#chain_form').serializeArray()));
        chainButton.disabled = true;

        errorMessage.textContent = "";
        errorMessage.style.visibility = "hidden";

        const chainFormDataObject = {
            session_id: session_id,
            action: 'chain_fee',
            form_data: formData,
            selected_capacity: selectedCapacity,
            selected_capacity_rate: selectedCapacityFeeRate,
            selected_chain_fee: selectedTransactionFeeRate
        };
        websocketSend(chainFormDataObject);
    }
    chainForm.onsubmit = chainFormSubmit;

}, false);

