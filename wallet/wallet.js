/*
* Chrome browser should be executed as follows for the local testing
* C:\Progra~2\Google\Chrome\Application\chrome.exe --user-data-dir="C:/Chrome dev session" --disable-web-security
*/

$(document).ready(function () {
    const derivationPath = "m/44'/60'/0'/0/";	
	
    var wallets = {};
	
    showView("viewSendTransaction");	
	initialize();
	setupWallet();

    $('#buttonClearForm').click(function () {
        showView("viewSendTransaction");
		clear();
    });

    $('#buttonSignTransaction').click(signTransaction);
    $('#buttonSendSignedTransaction').click(sendSignedTransaction);
	
	$('#buttonUrlForExplorer').click(function() {		
		url = $('#nodeAddress').val();
		uri = $('#urlForExplorer').val();
		senderAddress = $('#senderAddress').val();

		if(uri == 'utxo') { url = url + '/explorer/utxo:' + senderAddress;	}		
		else if(uri == 'blocksize') { url = url + '/explorer/block:size'; }
		else if(uri == 'txsize') { url = url + '/explorer/tx:size'; }
		else if(uri == 'miningblock') { url = url + '/mining/get-mining-job/' + senderAddress;}
		else return;
		
		explorer(url, explorer_callback);
		
	});	
	$('#buttonUrlForExplorer2').click(function() {		
		url = $('#nodeAddress').val();
		uri = $('#urlForExplorer2').val();
		
		if(uri == 'blockinfo') { url = url + '/explorer/block:' + $('#options').val();}		
		else if(uri == 'txinfo') { url = url + '/explorer/tx:' + $('#options').val(); }
		else if(uri == 'urlinfo') { url = url + '/'+ $('#options').val(); }
		else return;
		
		explorer(url, explorer_callback);
		
	});	
	$('#buttonUrlForExplorer3').click(function() {		
		uri = $('#nodeAddress').val() + '/' + $('#option1').val();
		msg = $('#option2').val();
		explorer_post(uri, explorer_callback, msg);		
	});	
	function explorer_callback(text) { 
		$('#textareaFindUtxoResult').val(text);
	} 
    function showView(viewName) {
        $('#' + viewName).show();
    }

    function showInfo(message) {
        $('#infoBox>p').html(message);
        $('#infoBox').show();
        $('#infoBox>header').click(function () {
            $('#infoBox').hide();
        })
    }

    function showError(errorMsg) {
        $('#errorBox>p').html('Error: ' + errorMsg);
        $('#errorBox').show();
        $('#errorBox>header').click(function () {
            $('#errorBox').hide();
        })
    }

    function showLoadingProgress(percent) {
        $('#loadingBox').html("Loading... " + parseInt(percent * 100) + "% complete");
        $('#loadingBox').show();
        $('#loadingBox>header').click(function () {
            $('#errorBox').hide();
        })
    }

    function hideLoadingBar() {
        $('#loadingBox').hide();
    }
	
    function initialize() {
		$('#nodeAddress').val("http://localhost:5000");
		clear();
	}
	function clear() {
		$('#transferValue').val('');
		$('#textareaFindUtxoResult').val('');
        $('#textareaSignedTransaction').val('');
        $('#textareaSendTransactionResult').val('');
		$('#recipientAddress').val("");
		$('#options').val("");
		$('#option1').val("");
		$('#option2').val("");
		$('#loadingBox').hide();
		$('#infoBox').hide();
		$('#errorBox').hide();
	}
    function signTransaction() {
        senderAddress = $('#senderAddress').val();
		if (!senderAddress)
			return showError("Invalid address!" + senderAddress);
		
		let recipient = $('#recipientAddress').val();
		if (!recipient)
			return showError("Invalid recipient!");
		
		let value = $('#transferValue').val();
		if (!value || value <= 0)
			return showError("Invalid transfer value!");		
		
		dateCreated = Date.parse(new Date());		
		
		let transaction = {
				"sender":senderAddress,			
				//"senderPubkey": "senderPublicKey", // TXOUT : scriptPub
				"dateCreated":dateCreated, // both
				// below four items can be multiple
				"recipient":recipient,  // TXOUT : in script
				"amount":value,  // TXOUT
				"senderSignature":"", // TXIN script : scriptSig
				"utxoId" :"",  // TXIN : 'utxoId + utxoIndex' matches one inique UTXO
				"utxoIndex":""  // TXIN
		};		
		
		nodeUri = $('#nodeAddress').val() + '/explorer/utxo:' + senderAddress;
		wallet = wallets[senderAddress];
		$('#textareaSignedTransaction').val("");
		explorer(nodeUri, findUTXOs);		
		//transaction.senderSignature = wallet.signMessage(transaction.utxoId);

		function findUTXOs(text) {	
			if(text == '[]' || text == "" || text == null) {
				return;
			}
			text = JSON.parse(text);
			if (text.length == 0) return;
	
			sum = 0;
			balance = 0;
			fee = transaction.amount * 0.01;
			txid_string = null;
			signed_string = null;
			tx_index = null;
			recipient = transaction.recipient;
			for (i = 0; i < text.length; i++) {				
				if (txid_string == null) {
					txid_string = text[i]['txId'];
					signed_string = wallet.signMessage(txid_string);
					tx_index = text[i]['txIdIndex'];
				} else {
					txid_string = txid_string + ',' + text[i]['txId'];
					signed_string = signed_string + ',' + wallet.signMessage(text[i]['txId']);
					tx_index = tx_index + ',' + text[i]['txIdIndex'];
				}
				sum = sum + text[i]['value']*1;
				if ( text[i]['value']*1 >= (transaction.amount*1 + fee)) {		
					transaction.utxoId = text[i]['txId'];
					transaction.utxoIndex = text[i]['txIdIndex'];
					transaction.senderSignature = wallet.signMessage(transaction.utxoId);	
					balance = text[i]['value']*1 - (transaction.amount*1 + fee);
					break;
				}				
				if (sum >= (transaction.amount*1 + fee)) {
					transaction.utxoId = txid_string;
					transaction.senderSignature =  signed_string;
					transaction.utxoIndex = tx_index;
					balance = sum - (transaction.amount*1 + fee);
					break;
				}
			}		
	
			if (sum < (transaction.amount*1 + fee)) {
				$('#textareaSignedTransaction').val("No enough coins to send");
				return;
			} else if (balance > 0) {   // balance is returned to the sender
				transaction.recipient = transaction.recipient + ',' + senderAddress;
				transaction.amount = transaction.amount + ',' + balance;
			}
			
			$('#textareaSignedTransaction').val(JSON.stringify(transaction));
		}		
    }
    function sendSignedTransaction() {
        let signedTransaction = $('#textareaSignedTransaction').val();
		let nodeUri = $('#nodeAddress').val() + '/transactions/new';
		
		var xhttp = new XMLHttpRequest();
		xhttp.onreadystatechange = function() {
			$('#textareaSendTransactionResult').val(this.responseText);
		};
		xhttp.open("POST", nodeUri, true);
		xhttp.setRequestHeader("Content-type", "application/json");
		xhttp.send(signedTransaction);
    }
	/*
	* json = { a:1, b:2, c:3}
	* string=JSON.stringify(json)
	* JSON.parse(string)
	*/
	async function explorer(uri, callback) {	
		var xhttp = new XMLHttpRequest();
		var text = null;
		xhttp.onreadystatechange = function() {
			callback(this.responseText);
		};
		xhttp.open("GET", uri, true);
		xhttp.setRequestHeader("Content-type", "application/json");
		xhttp.send();
	}
	async function explorer_post(uri, callback, message) {	
		var xhttp = new XMLHttpRequest();
		xhttp.onreadystatechange = function() {
			callback(this.responseText);
		};
		xhttp.open("POST", uri, true);
		xhttp.setRequestHeader("Content-type", "application/json");
		xhttp.send(message);
	}
	/*
	* Setup an address for the wallet
	* 
	*/
	function setupWallet() {
		let senderPrivateKey = [ "0xbe8cad6b7dc050c26baf9f4bc2fc7e505e0c3b00e01c761d0b482ca7905e2922",
								 "0xb555bed06f4c30951f940b5f755350572f51f91d318d429f82928b8074e36402",
								 "0x78139d0777ba8ddd229a775986f555cbc9e8b1d9cf9f8bda80646dfe70e30fcc",
								 "0xdfe8cf1a22364200b803842d784b018ac48e6b775d6246d6159ba767ace14a85" 
		];
		for (i = 0; i < senderPrivateKey.length; i++) {
			wallet = new ethers.Wallet(senderPrivateKey[i]);
			wallets[wallet.address] = wallet;
		}
	}
});