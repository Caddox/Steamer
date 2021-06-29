// This file uses jquery

$(document).ready(function() {
    $("#steamer-setup-download-submit").click(function() {
        // Build the data struct to send to 
        st = $("#steamer-start-time").val();
        et = $("#steamer-end-time").val();
        console.log(st, et);

        app_id = window.location.pathname.split('/').reverse()[0];
        app_id = parseInt(app_id);

        payload = {
            "start_hour": st.split(':')[0],
            "start_min": st.split(':')[1],
            "end_hour": et.split(':')[0],
            "end_min": et.split(':')[1],

            "app_id": app_id
        };

        $.ajax({
            url: window.location.href + "/download",

            data: JSON.stringify(payload),
            contentType: "application/json",
            type: 'POST',

        });
    });
});