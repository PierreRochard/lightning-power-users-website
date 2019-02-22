
document.addEventListener('DOMContentLoaded', async function () {

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

        const selectedCapacity = parseInt(capacitySelect.selectedOptions[0].value);
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

        const selectedCapacityFeeRate = parseFloat(capacityFeeRateSelect.selectedOptions[0].value);
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
        } else {
            document.querySelector('#capacity-fee').innerHTML = '-';
            document.querySelector('#capacity-fee-usd').innerHTML = '-';
        }

        const selectedTransactionFeeRate = parseInt(transactionFeeRateSelect.selectedOptions[0].value);
        document.querySelector('#transaction-fee-rate').innerHTML = selectedTransactionFeeRate.toLocaleString();

        const expectedBytes = parseInt(document.querySelector('#expected-bytes').innerHTML);
        const transactionFee = selectedTransactionFeeRate * expectedBytes;
        const transactionFeeUsd = Math.round(transactionFee * pricePerSat * 100) / 100;
        document.querySelector('#transaction-fee').innerHTML = transactionFee.toLocaleString();
        document.querySelector('#transaction-fee-usd').innerHTML = transactionFeeUsd.toLocaleString(undefined, {
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

