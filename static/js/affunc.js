$('.add-feed').each(function() {
    var plusButton = $(this);
    $(this).click(function() {
        var feedId = $(plusButton).prev().data('feed-id');
        var resp = $.ajax('/assignfeed/' + feedId, {async: false});
        if (resp.responseText === '1') {
            $(plusButton).remove();
        }
    });
});