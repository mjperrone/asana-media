function get_title() {
    var url_field = $("#url");
    var url = url_field.val();
    var title_field = $("#title");
    if (url) {
      $.get("suggest_title", {url: url}, function(response){
        if(response.title){
          title_field.val(response.title);
        } else {
          // TODO: say sorry
        }
      });
    }
}
