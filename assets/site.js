// BattleSpinners — petits comportements du site. Tout reste utilisable sans JavaScript.
(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // 1. Boucles vidéo : lecture seulement quand elles sont visibles, jamais si
  //    l'utilisateur a demandé à réduire les animations (elles gardent alors leurs contrôles).
  var loops = document.querySelectorAll("video.loop");
  if (!reduceMotion && "IntersectionObserver" in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var video = entry.target;
        if (entry.isIntersecting) {
          var playing = video.play();
          if (playing && playing.catch) { playing.catch(function () {}); }
        } else {
          video.pause();
        }
      });
    }, { threshold: 0.25 });
    loops.forEach(function (video) {
      video.removeAttribute("controls");
      video.muted = true;
      observer.observe(video);
    });
  }

  // 2. Lecteur YouTube chargé seulement au clic : aucun appel à YouTube avant.
  document.querySelectorAll("button.yt").forEach(function (button) {
    button.addEventListener("click", function () {
      var id = button.getAttribute("data-youtube-id");
      if (!id) { return; }
      var iframe = document.createElement("iframe");
      iframe.src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(id) + "?autoplay=1&rel=0";
      iframe.title = button.getAttribute("data-title") || "Trailer";
      iframe.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
      iframe.allowFullscreen = true;
      var holder = document.createElement("div");
      holder.className = "yt notch";
      holder.appendChild(iframe);
      button.replaceWith(holder);
    });
  });

  // 3. Boutons « Copier » pour les textes que les médias reprennent tels quels.
  document.querySelectorAll("[data-copy]").forEach(function (button) {
    button.hidden = !navigator.clipboard;
    button.addEventListener("click", function () {
      var target = document.getElementById(button.getAttribute("data-copy"));
      if (!target) { return; }
      var text = target.innerText.trim();
      navigator.clipboard.writeText(text).then(function () {
        var label = button.textContent;
        button.textContent = button.getAttribute("data-done-label") || "Copied";
        button.setAttribute("data-done", "");
        setTimeout(function () {
          button.textContent = label;
          button.removeAttribute("data-done");
        }, 2000);
      });
    });
  });
})();
