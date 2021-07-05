// This file uses jQuery
$(document).ready(function() {
    $("#steamer-settings-input-os").keydown(function(e) {
        if(e.keyCode == 13) {
            append_new_os();
        }
    });

    $('#steamer-settings-add-os').click(function() {
        append_new_os();
    });

    $("#steamer-settings-input-language").keydown(function(e) {
        if(e.keyCode == 13) {
            append_new_language();
        }
    });

    $('#steamer-settings-add-language').click(function() {
        append_new_language();
    });


    // Send data to the sever
    $("#steamer-settings-submit-button").click(function() {
        // Send new information to the sever
        payload = {
            download_location: $("#steamer-settings-dl-path").val(),
            os_list: [],
            languages: [],
        };
        console.log(payload);

        // Read in the os filters and language filters.
        payload.os_list = get_filters("#steamer-settings-os-filters");
        payload.languages = get_filters("#steamer-settings-language-filters");


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

$(document).on("click", ".remove", function() {
    $(this).parent().remove();
});

function append_new_os() {
    var new_val = $('#steamer-settings-input-os').val();
    $('#steamer-settings-input-os').val('');

    $('#steamer-settings-os-filters').find('ul').append(
        '<li>' + new_val + 
        "<span class='remove'>x</span>" +
        '</li>'
    );
}

function append_new_language() {
    var new_val = $('#steamer-settings-input-language').val();
    $('#steamer-settings-input-language').val('');

    $('#steamer-settings-language-filters').find('ul').append(
        '<li>' + new_val + 
        "<span class='remove'>x</span>" +
        '</li>'
    );
}

function get_filters(search_tag) {
    filter_list = [];
    $(search_tag).find('li').each(function(index) {
         filter_list.push($(this).text().slice(0, -1));
    });
    return filter_list;
}