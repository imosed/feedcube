$('.content-section').each(
    function() {
        var feedId = $(this).data('feed-id');
        var responseContent = $.ajax('/viewfeed/' + feedId, {async: false});
        $(this).html(responseContent.responseText);
    }
);