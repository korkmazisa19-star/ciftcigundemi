/* Çiftçi Gündemi — haber bildirimleri service worker */
importScripts("https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js");
firebase.initializeApp({
  apiKey: "AIzaSyCFacQOHSwfbsbPsmVuM_xmncBrZphK3XU",
  authDomain: "ciftcigundemi.firebaseapp.com",
  projectId: "ciftcigundemi",
  messagingSenderId: "962026471192",
  appId: "1:962026471192:web:9c3cb319231fdb5350e86d"
});
firebase.messaging();
self.addEventListener("notificationclick", function (e) {
  var link = (e.notification && e.notification.data && (e.notification.data.link || (e.notification.data.FCM_MSG && e.notification.data.FCM_MSG.data && e.notification.data.FCM_MSG.data.link))) || "/";
  e.notification.close();
  e.waitUntil(clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (l) {
    for (var i = 0; i < l.length; i++) if (l[i].url === link && "focus" in l[i]) return l[i].focus();
    return clients.openWindow(link);
  }));
});
