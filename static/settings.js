// This file uses jQuery

$(document).ready(function() {
    // Add the current text to the boxes
    $.ajax({
        url: window.location.origin + "/api/v1/settings",

        success: function(data) {
            $("#steamer-settings-dl-path").val(data.download_location);

            // Update message log
            $("#steamer-message-log").append(
                '<p>Got Settings from server!</p>'
            );
        }
    });

    $("#steamer-settings-submit-button").click(function() {
        // Send new information to the sever
        payload = {
            download_location: $("#steamer-settings-dl-path").val(),
        };


        $.ajax({
            url: window.location.origin + "/api/v1/settings/set",
            type: "POST",
            contentType: "application/json",

            data: JSON.stringify(payload),

            success: function(data) {
                $("#steamer-message-log").append(
                    '<p>' + data.response + '</p>'
                );
            },
        });
    });
});
