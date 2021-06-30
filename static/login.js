// This file uses Jquery

$(document).ready(function() {
    // On starting to run, hide the 2fa and email boxes until they're needed;
    $('#steamer-2fa-div').hide();
    $('#steamer-email-code-div').hide();

    // On the login click
    $('#steamer-user-pass-submit').click(function() {
        // Send an ajax POST to "/login":
        var payload = {
            "username":   $('#steamer-username').val(),
            "password":   $('#steamer-password').val(),
            "2fa":        $('#steamer-2fa').val(),
            "email-code": $('#steamer-email-code').val()
        };

        console.log(payload);
        $.ajax({
            url: window.location.origin + "/api/v1/login",

            data: JSON.stringify(payload),
            contentType: "application/json",
            type: "POST",

            success: function(data) {
                login_result_handler(data);
            },
        });
    });
});

function login_result_handler(data) {
    console.log(data);

    // Form for incoming data:
    /*
        data.success: bool => If true, the login was successfull. Otherwise, read the other fields.
        data.target: string => Target for the error reason (password, email-code, 2fa, steam)
        data.reason: string => String stating the reason for the target failure.
    */
    if(data.success == true) {
        alert("Login successfull!");
        location.href = location.origin;
        return;
    }

    $("steamer-server-log").prepend(
        "<p>" + data.reason + "</p>"
    )

    if(data.target === "2fa") {
        // Show the 2fa box.
        $('#steamer-2fa-div').show();
    }
    else if (data.target === "email-code") {
        // Show the email box.
        $("#steamer-email-code-div").show();
    }

}