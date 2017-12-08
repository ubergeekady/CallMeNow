console.debug("CallMeNow Javascript SDK v1.0.0 loaded");

// Read queue
var q = window.callmenow.q;

//var url = 'http://staging.callmenowhq.com/app/api/';
var callmenow_base_url = 'http://127.0.0.1:8000'
var callmenow_url = callmenow_base_url+'/widgetapi/';

// Utility functions
var cm = {
  // Get document element by ID
  getId: function(id) {
    return document.getElementById(id);
  },

  // Xhr request for GET and POST
  xhr: function(method, url, data, response, onready) {
    var xhr = new XMLHttpRequest();
    xhr.open(method, url, true);
    xhr.setRequestHeader('Content-type', 'application/json;charset=UTF-8');
    xhr.responseType = response;
    xhr.send(data);
    xhr.onreadystatechange = function() {
      if (this.readyState == 4 && this.status == 200) {
        onready(this.response);
      }
    };
  }
};

// Availability
var callmenow = function(wid) {
  console.debug('Checking call availability for ' + wid);
  cm.xhr('GET', callmenow_url + 'available/' + wid + '/', null, 'json', function(r) {
    if(r.live) {
      console.debug('Widget is live');

      // if(!r.showonmobile) {
      //   console.debug('Not showing on mobile');
      //   return;
      // }

      if(!r.available && !r.captureleads) {
        console.debug('No agents available and not capturing leads');
        return;
      }

      // Get widget HTML and CSS
      cm.xhr('GET', callmenow_base_url+r.html, null, null, function(h) {
        var html = document.createElement('div');
        html.className = 'callmenow';
        html.innerHTML = h;
        document.body.appendChild(html);

        // Set widget button
        cm.getId('callmenow-btn').src = callmenow_base_url+r.img;

        // Widget position
        if(r.style.position == 'left') {
          cm.getId('callmenow').classList.add('callmenow-left');
          cm.getId('callmenow-wid').classList.add('callmenow-btn-left');
        } else {
          cm.getId('callmenow').classList.add('callmenow-right');
          cm.getId('callmenow-wid').classList.add('callmenow-btn-right');
        }

        // Agent Name & Message
        //cm.getId('callmenow-alert-agent').innerHTML = r.alert.name;
        cm.getId('callmenow-alert-message').innerHTML = r.alert.message;
        var alert = cm.getId('callmenow-alert').style;
        alert.color = r.style.alert.color;
        alert.backgroundColor = r.style.alert.background;

        // Body style
        var body = cm.getId('callmenow-body').style;
        body.color = r.style.body.color;
        body.backgroundColor = r.style.body.background;

        // Close
        cm.getId('callmenow-close').onclick = function() {
          cm.getId('callmenow-body').classList.add('callmenow-hide');
        };

        // Accept only numbers for phone
        cm.getId('callmenow-call-phone').onkeypress = function(e) {
          if(cm.getId('callmenow-call-phone').value.length < 1) {
            cm.getId('callmenow-call-phone').value = '+';
          }
          if(e.charCode == 0 || !isNaN(e.key)) {
            return;
          }
          e.preventDefault();
        };

        // Validate phone number
        var phoneValidate = function(phone) {
          if(phone.length < 8)  {
            console.debug('Invalid phone number');
            cm.getId('callmenow-call-phone').style.borderColor = 'red';
            setTimeout(function() {
              cm.getId('callmenow-call-phone').style = null;
            }, 3000);
            return false;
          }
          return true;
        };

        // Phone country code
        cm.getId('callmenow-call-phone').value = r.code;

        // Lead date and time
        /*date = cm.getId('callmenow-call-date');
        r.date.forEach(function(e) {
          var o = document.createElement('option');
          o.value = e;
          o.innerHTML = e;
          date.appendChild(o);
        });*/
        time = cm.getId('callmenow-call-time');
        r.time.forEach(function(e) {
          var o = document.createElement('option');
          o.value = e;
          o.innerHTML = e;
          time.appendChild(o);
        });

        // Call later
        cm.getId('callmenow-call-later').onclick = function() {
          cm.getId('callmenow-now').classList.add('callmenow-hide');
          cm.getId('callmenow-later').classList.remove('callmenow-hide');
        };

        // Alert show
        //Added - show alert only when available
        //Also - added duration
        if(r.available){
            if(r.showalert) {
              setTimeout(function() {
                if(cm.getId('callmenow-body').classList.contains('callmenow-hide')) {
                  cm.getId('callmenow-alert').classList.remove('callmenow-hide');
                  if(r.playsoundonalert){
                    new Audio(callmenow_base_url+'/static/widget/open.mp3').play()
                  }
                }
              }, r.showalert_after);
            }
        }

        // Hide alert and show body
        var showBody = function() {
          cm.getId('callmenow-alert').classList.add('callmenow-hide');
          cm.getId('callmenow-body').classList.remove('callmenow-hide');
        };

        // Onclick button and alert
        cm.getId('callmenow-alert').onclick = showBody;
        cm.getId('callmenow-btn').onclick = showBody;

        if(r.available) {
          console.debug('Agents are available');
          // Call
          cm.getId('callmenow-body-message').innerHTML = r.call.message;
        } else {
          console.debug('Agents are not available');
          // Lead
          cm.getId('callmenow-body-message').innerHTML = r.lead.message;
          if(r.captureleads) {
            console.debug('Capturing leads');
            cm.getId('callmenow-now').classList.add('callmenow-hide');
            cm.getId('callmenow-later').classList.remove('callmenow-hide');
          }
        }

        // Onclick call
        cm.getId('callmenow-call-now').onclick = function() {
          var phone = cm.getId('callmenow-call-phone').value;
          if(!phoneValidate(phone)) {
            return;
          }

          cm.xhr('POST', callmenow_url + 'newcall/' + wid + '/', JSON.stringify({phone: phone}), 'json', function(s) {
            if(s.callmenow_status == 'call-failed') {
              console.debug('New call failed: ' + s.callmenow_comments);
              cm.getId('callmenow-body-message').innerHTML = "Call Failed<br /><br /><img src='"+callmenow_base_url+"/static/widget/missedcall.png'><br /><br />"+s.callmenow_comments
            }
            if(s.callmenow_status == 'call-queued') {
              console.debug('New call queued: ' + s.callmenow_comments);
              cm.getId('callmenow-body-message').innerHTML = "Your call is being processed.<br /><br /><img src='"+callmenow_base_url+"/static/widget/queue.gif'><br />You are currently the "+s.queue+"th person to order the call. "
              //cm.getId('callmenow-body-sub').innerHTML = "";
            }

            //cm.getId('callmenow-body-message').innerHTML = s.callmenow_comments;
            //cm.getId('callmenow-body-sub').innerHTML = '';
            cm.getId('callmenow-call').classList.add('callmenow-hide');

            /*if(s.count) {
              var callmenowCount = setInterval(function() {
                if(s.count <= 0) {
                  cm.getId('callmenow-body-sub').innerHTML = '';
                  clearInterval(callmenowCount);
                }
                cm.getId('callmenow-body-sub').innerHTML = s.count--;
              }, 1000);
            }*/

            var callmenowInt = setInterval(function() {
              console.debug('callstatus ' + s.callmenow_uuid + " " + s.callmenow_status);
              cm.xhr('GET', callmenow_url + 'callstatus/' + s.callmenow_uuid, null, 'json', function(s) {
                console.debug(s.callmenow_status);
                if(s.callmenow_status == 'call-queued') {
                    cm.getId('callmenow-body-message').innerHTML = "Your call is being processed.<br /><br /><img src='"+callmenow_base_url+"/static/widget/queue.gif'><br />You are currently the "+s.queue+"th person to order the call. "
                    //cm.getId('callmenow-body-sub').innerHTML = 'image';
                }
                if(s.callmenow_status == 'call-connecting') {
                    cm.getId('callmenow-body-message').innerHTML = "Call connecting<br /><br /><img src='"+callmenow_base_url+"/static/widget/ringing.gif'><br />"
                    //cm.getId('callmenow-body-sub').innerHTML = 'image';
                }
                if(s.callmenow_status == 'call-inprogress') {
                    cm.getId('callmenow-body-message').innerHTML = "In conversation<br /><br /><img src='"+callmenow_base_url+"/static/widget/oncall.gif' width=200 height=200><br />"
                    //cm.getId('callmenow-body-sub').innerHTML = "Img"
                }
                if(s.callmenow_status == 'call-failed') {
                    clearInterval(callmenowInt);
                    cm.getId('callmenow-body-message').innerHTML = "Call Failed<br /><br /><img src='"+callmenow_base_url+"/static/widget/missedcall.png'><br /><br />"+s.callmenow_comments
                    setTimeout(function() {
                        //cm.getId('callmenow-body-sub').innerHTML = s.callmenow_status + s.callmenow_comments
                        cm.getId('callmenow-body').classList.add('callmenow-hide');
                    }, 4000);

                }
                if(s.callmenow_status == 'call-completed') {
                    clearInterval(callmenowInt);
                    cm.getId('callmenow-body-message').innerHTML = "Call Completed. Thank You<br /><br /><img src='"+callmenow_base_url+"/static/widget/hangup.jpg' width=200 height=200><br /><br />"
                    setTimeout(function() {
                        //cm.getId('callmenow-body-sub').innerHTML = s.callmenow_status + s.callmenow_comments
                        cm.getId('callmenow-body').classList.add('callmenow-hide');
                    }, 4000);
                }
                //cm.getId('callmenow-body-message').innerHTML = s.callmenow_comments;
              });
            }, 3000);
          });
        };

        // Onclick lead
        cm.getId('callmenow-lead').onclick = function() {
          var phone = cm.getId('callmenow-call-phone').value;
          if(!phoneValidate(phone)) {
            return;
          }
          //var date = cm.getId('callmenow-call-date').value;
          var time = cm.getId('callmenow-call-time').value;

          var data = {
            phone: phone,
            //date: date,
            time: time
          };

          cm.xhr('POST', callmenow_url + 'newlead/' + wid + '/', JSON.stringify(data), 'json', function(s) {
            if(s.status) {
              console.debug('New lead created');
            } else {
              console.debug('New lead failed: ' + s.message);
            }
            cm.getId('callmenow-body-message').innerHTML = s.message;
            cm.getId('callmenow-call').classList.add('callmenow-hide');
            setTimeout(function() {
              cm.getId('callmenow-body').classList.add('callmenow-hide');
            }, 3000);
          });
        };
      });
    }
  });
};

// Execute queue
q.forEach(function(args) {
  callmenow.apply(null, args);
});
