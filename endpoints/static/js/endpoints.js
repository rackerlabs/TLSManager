// get CSRF cookie value for AJAX
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// this uses the above function to place the CSRF token in the HTTP header
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
            // Only send the token to relative URLs i.e. locally.
            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
    }
});


// this function handles the highlighting
// in the left hand side menu
$(function() {
  function stripTrailingSlash(str) {
    if(str.substr(-1) == '/') {
      return str.substr(0, str.length - 1);
    }
    return str;
  }

  var url = window.location.pathname;  
  var activePage = stripTrailingSlash(url);

  $('.nav li a').each(function() {
    $(this).parent().removeClass("active");
    var currentPage = stripTrailingSlash($(this).attr('href'));

    if (activePage == currentPage) {
      $(this).parent().addClass('active'); 
    } 
  });
});


// -------- URL section -----------

// this function is used in Change URL Details to
// populate that screen before user makes changes
function populateChangeURLForm(selector) {
    //var value = sel.value;
    endpoint_id = document.getElementById("id_urls").value;
    $.ajax({
       url: "/getChangeURLDetails",
       type: "POST",
       data: { "endpoint_id" : endpoint_id },
       dataType : "JSON",
       success: successChangeURL
    });
}

function successChangeURL(response) {
    document.getElementById("id_prod_name").value = response.product_name;
    document.getElementById("save_endpoint_id").value = response.endpoint_id;
    alert(response.product_name);
}

// this function is used in Change URL Details page to
// delete that record if the user clicks on the Delete button
function confirmURLDelete() {
    //var value = sel.value;
    endpoint_id = document.getElementById("save_endpoint_id").value;
    $.ajax({
       url: "/deleteURLDetails",
       type: "GET",
       data: { "endpoint_id" : endpoint_id },
       dataType : "JSON",
       success: successDeleteURL
    });
}

function successDeleteURL(response) {
    //document.getElementById("id_prod_name").value = response.product_name;
    alert('URL was deleted');
}


// -------- Submit scan section -----------

// this function handles the Scan URL Now functionality
function submitForScan(endpoint_id) {
    //alert("endpoint_id: " + endpoint_id);
    //endpoint_id = document.getElementById("id_urls").value;
    var csrftoken = getCookie('csrftoken');
    //alert('endpoint_id=' + endpoint_id + '  csrftoken=' + csrftoken); // sendEmailToContact
    $.ajax({
       url: "/submitForScan",
       type: "GET",
       data: { "endpoint_id" : endpoint_id },
       dataType : "JSON",
       success: successSubmitForScan,
        error: errorSubmittingForScan
    });
}

function successSubmitForScan(response) {
    //document.getElementById("id_prod_name").value = response.product_name;
    alert("Submitted For Scan");
}

function errorSubmittingForScan(xhr, ajaxOptions, thrownError) {
    //document.getElementById("id_prod_name").value = response.product_name;
    alert("Error when Submitted For Scan");
}


// -------- Send email section -----------

// this is used in the Test Details page to send email to contact in
// the current test
function sendEmail(result_id) {
    //var csrftoken = getCookie('csrftoken');
    //alert('result_id=' + result_id + '  csrftoken=' + csrftoken); // sendEmailToContact
    $.ajax({
       url: "/sendEmailToContact/",
       type: "POST",
       data: { "result_id" : result_id },
       dataType : "JSON",
       success: successSendEmail,
       error: errorSendEmail
    }); 
}

function successSendEmail(response) {
    alert("Email sent");
    //window.location.href = "/dashboard";
    return false;
}

function errorSendEmail(xhr, ajaxOptions, thrownError) {
    alert('got error');
}


// -------- Test Details section -----------

// this is used in the Test Details page to return to
// the Test Results List
function returnToResultsList(result_id, page2return2) {
    //alert('returnToResultsList');
    window.location.href = "/dashboard/" + page2return2;
    return false;
}

// this is used in the Test Details page to delete
// the current test
function confirmTestResultDelete(result_id) {
        $.ajax({
           url: "/deleteTestResultDetails",
           type: "GET",
           data: { "result_id" : result_id },
           dataType : "JSON",
           success: successTestResultDelete,
           error: errorTestResultDelete
        }); 
}

function successTestResultDelete(response) {
    alert(response.message);
    window.location.href = "/dashboard";
    return false;
}

function errorTestResultDelete(xhr, ajaxOptions, thrownError) {
    alert('got error');
}

// confirm delete
$('#confirm-delete').on('show.bs.modal', function(e) {
    $(this).find('.btn-ok').attr('href', $(e.relatedTarget).data('href'));
    //$('.debug-url').html('Delete URL: <strong>' + $(this).find('.btn-ok').attr('href') + '</strong>');
});


// -------- Contact section -----------

// this function is used in Change Contacts to
// populate that screen before user makes changes
function populateContactForm(selector) {
    //var value = selector.value;
    contact_id = document.getElementById("id_emails").value;
    if (contact_id == 'pleaseselect')
        return;
    $.ajax({
       url: "/getChangeContact",
       type: "GET",
       data: { "contact_id" : contact_id },
       dataType : "JSON",
       success: successGetContact
    });
}

function successGetContact(response) {
    document.getElementById("id_firstname").value = response.firstname;
    document.getElementById("id_lastname").value = response.lastname;
    //alert(response.firstname);
}

function validateContact() {
    //if (document.getElementById("id_emails").value == "pleaseselect") {
    //    alert('Please select email');
    //    return false;
    //}
    if (document.getElementById("id_firstname").value == null) {
        alert('Please enter first name');
        return false;
    }
    if (document.getElementById("id_lastname").value == null) {
        alert('Please enter last name');
        return false;
    }
    return true;
}

function changeContact() {
    if (validateContact())
		contact_id = document.getElementById("id_emails").value;
		firstname = document.getElementById("id_firstname").value;
		lastname = document.getElementById("id_lastname").value;
		$.ajax({
		   url: "/updateContact",
		   type: "POST",
		   data: { "contact_id" : contact_id, "firstname": firstname, "lastname": lastname },
		   dataType : "JSON",
		   success: successUpdateContact,
		   error: errorUpdateContact
		}); 
	//return false;	// prevent form submission for AJAX
}

function successUpdateContact(response) {
    alert('Contact update was successful');
    //window.location.href = "/changeContact";
    return false;
}

function errorUpdateContact(xhr, ajaxOptions, thrownError) {
    alert('got error updating contact ' + thrownError);
}

// this is used in the change Contact page to delete
// the current contact
function confirmContactDelete(contact_id) {
        $.ajax({
           url: "/deleteContact",
           type: "GET",
           data: { "contact_id" : contact_id },
           dataType : "JSON",
           success: successContactDelete,
           error: errorContactDelete
        }); 
}

function successContactDelete(response) {
    alert(response.message);
    window.location.href = "/changeContact";
    return false;
}

function errorContactDelete(xhr, ajaxOptions, thrownError) {
    alert('got error deleting contact');
}


// -------- Product section -----------

function validateProduct() {
    if (document.getElementById("id_products").value == "pleaseselect") {
        alert('Please select product');
        return false;
    }
    if (document.getElementById("id_contacts").value == "pleaseselect") {
        alert('Please select email');
        return false;
    }
    return true;
}

function changeProduct() {
    if (validateProduct())
        product_id = document.getElementById("id_products").value
        alert('product_id=' + product_id)
        contact_id = document.getElementById("id_contacts").value
        alert('contact_id=' + contact_id)
        $.ajax({
           url: "/updateProduct",
           type: "POST",
           data: { "product_id" : product_id, "contact_id" : contact_id },
           dataType : "JSON",
           success: successUpdateProduct,
           error: errorUpdateProduct
        }); 
}

function successUpdateProduct(response) {
    alert('Product update was successful');
    //window.location.href = "/changeProduct";
    return false;
}

function errorUpdateProduct(xhr, ajaxOptions, thrownError) {
    alert('got error updating product ' + thrownError);
}

