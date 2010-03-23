/**
 * Returns on the form:
 * 800 -> 800 B
 * 1024 -> 1 KB
 * 1024*1024 -> MB
 */
function pp_bytes(bytes) {
  
  var temp = '';
  if (bytes < 1024) {
    temp ='B';
  } else if (bytes < 1048576) {
    bytes = bytes/1024;
    temp = 'KB';
  } else if (bytes < 1073741824) {
    bytes = bytes/1048576;
    temp = 'MB';
  } else if (bytes < 1099511627776) {
    bytes = bytes/1073741824;
    temp = 'GB';
  }
  
  return bytes.toFixed(2)+' '+temp;
  
}

function pp_date(time) {
  
  var aDate = new Date(time*1000);
  return  aDate.getFullYear() + '-'+
          pp_prefix(aDate.getDate()) + '-'+
          pp_prefix(aDate.getMonth()) + ' '+
          pp_prefix(aDate.getHours()) + ':'+
          pp_prefix(aDate.getMinutes());
  
}

function pp_prefix(test) {
  
  if (test < 10) {
    test = "0"+test;
  }
  
  return test;
}
