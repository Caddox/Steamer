$(document).ready(function () {
    $("#steamer-populate-games").click(function() {
        $.ajax({
            url: location.origin + "/api/v1/populate",

            success: function(data) {
                location.reload();
            },
        });
    });
});