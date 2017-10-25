$('.assigned-feed').each(function() {
    $(this).mouseenter(function() {
        var feedId = $(this).children('.feed-content').data('feed-id');
        var feedTile = $(this);
        var removeButton = document.createElement('div');
        $(removeButton).html('&times;');
        $(removeButton).attr('class', 'remove-feed');
        $(removeButton).click(function() {
            var uaReq = $.ajax('/unassignfeed/' + feedId, {async: false});
            if (uaReq.responseText === '1') {
                $(feedTile).remove();
            }
        });
        $(this).find('.tile-link').css('display', 'block').css('width', '86%');
        $(this).children('.link-container').append(removeButton);
    }).mouseleave(function() {
        $('.remove-feed').remove();
        $(this).find('.tile-link').css('display', 'unset').css('width', '100%');
    });
});
