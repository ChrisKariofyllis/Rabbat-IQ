(function () {
  const node = document.getElementById("store-map");
  const dataNode = document.getElementById("store-map-data");
  const note = document.getElementById("map-note");
  if (!node || !dataNode || typeof L === "undefined") {
    if (note) {
      note.textContent = "The street map did not load. Distances in the list are unchanged.";
    }
    return;
  }

  let payload;
  try {
    payload = JSON.parse(dataNode.textContent || "");
  } catch (_error) {
    if (note) {
      note.textContent = "The street map did not load. Distances in the list are unchanged.";
    }
    return;
  }

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  node.replaceChildren();
  node.setAttribute("aria-busy", "true");

  const map = L.map(node, {
    scrollWheelZoom: false,
    zoomControl: true,
    attributionControl: true,
  });
  map.zoomControl.setPosition("topright");
  map.attributionControl.setPrefix("");
  node.setAttribute("aria-label", "Map of stores inside the search radius");

  const homeLat = payload.home ? Number(payload.home.lat) : NaN;
  const homeLon = payload.home ? Number(payload.home.lon) : NaN;
  const hasHome = Number.isFinite(homeLat) && Number.isFinite(homeLon);
  const first = (payload.stores || []).find((store) => Number.isFinite(Number(store.lat)) && Number.isFinite(Number(store.lon)));
  if (hasHome) {
    map.setView([homeLat, homeLon], 13);
  } else if (first) {
    map.setView([Number(first.lat), Number(first.lon)], 13);
  } else {
    map.setView([51.16, 10.45], 6);
  }

  const quietNote = payload.home
    ? "The circle is your search radius, and You is the postal code."
    : "Saved branch coordinates. Set a postal code and scan to place You and the radius.";
  let tilesReady = false;

  function showFailure() {
    if (!note || tilesReady) {
      return;
    }
    note.textContent = "Street tiles did not load. The circle and markers still use the saved coordinates.";
    node.setAttribute("aria-busy", "false");
  }

  const tiles = L.tileLayer("https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png", {
    maxZoom: 20,
    subdomains: "abc",
    updateWhenIdle: true,
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.openstreetmap.fr/">OpenStreetMap France</a>',
  });
  tiles.on("tileerror", showFailure);
  tiles.on("load", () => {
    tilesReady = true;
    node.setAttribute("aria-busy", "false");
    if (note) {
      note.textContent = quietNote;
    }
  });
  tiles.addTo(map);
  window.setTimeout(showFailure, 8000);

  const markers = new Map();
  const bounds = L.latLngBounds([]);

  function cssColor(value) {
    return /^var\(--chain-[a-z0-9-]+\)$/.test(value) ? value : "var(--chain-fallback-1)";
  }

  function cssTone(value) {
    return /^[a-z]{0,24}$/.test(value || "") ? value || "" : "";
  }

  function row(id) {
    return document.querySelector('.store-list li[data-store-id="' + id + '"]');
  }

  let hotId = null;

  function setHot(id) {
    if (hotId === id) {
      return;
    }
    if (hotId !== null) {
      const previous = markers.get(hotId);
      if (previous) {
        previous.setZIndexOffset(0);
        previous.getElement()?.classList.remove("is-hot");
      }
      row(hotId)?.classList.remove("is-hot");
    }
    hotId = id;
    if (id === null) {
      return;
    }
    const marker = markers.get(id);
    if (marker) {
      marker.setZIndexOffset(700);
      marker.getElement()?.classList.add("is-hot");
    }
    row(id)?.classList.add("is-hot");
  }

  (payload.stores || []).forEach((store) => {
    const lat = Number(store.lat);
    const lon = Number(store.lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
      return;
    }
    const id = String(store.id);
    if (!/^[0-9]+$/.test(id)) {
      return;
    }
    const tone = cssTone(store.tone);
    const toneAttr = tone ? ' data-tone="' + tone + '"' : "";
    const marker = L.marker([lat, lon], {
      icon: L.divIcon({
        className: "store-pin",
        html: '<span class="pin-dot"' + toneAttr + ' style="--pin: ' + cssColor(store.color) + '"></span>',
        iconSize: [18, 18],
        iconAnchor: [9, 9],
      }),
      keyboard: true,
      riseOnHover: true,
      title: store.name || "Store",
    });
    marker.addTo(map);
    markers.set(id, marker);
    bounds.extend([lat, lon]);
    marker.on("mouseover", () => setHot(id));
    marker.on("mouseout", () => setHot(null));
    marker.on("click", () => {
      setHot(id);
      row(id)?.scrollIntoView({ block: "nearest" });
    });
    const item = row(id);
    if (!item) {
      return;
    }
    item.addEventListener("pointerenter", () => setHot(id));
    item.addEventListener("pointerleave", (event) => {
      if (event.pointerType === "touch") {
        return;
      }
      setHot(null);
    });
    item.addEventListener("click", () => {
      setHot(id);
      map.panTo(marker.getLatLng(), { animate: !reduceMotion, duration: 0.25 });
    });
  });

  if (hasHome) {
    const home = [homeLat, homeLon];
    const radius = Number(payload.radiusM);
    if (Number.isFinite(radius) && radius > 0) {
      const circle = L.circle(home, {
        radius: radius,
        color: "#1e6a43",
        weight: 1.5,
        opacity: 0.9,
        fillColor: "#1e6a43",
        fillOpacity: 0.08,
      });
      circle.addTo(map);
      bounds.extend(circle.getBounds());
    } else {
      bounds.extend(home);
    }
    L.marker(home, {
      icon: L.divIcon({
        className: "you-marker",
        html: '<span class="you-pin"><span class="you-label">You</span><span class="you-dot"></span></span>',
        iconSize: [56, 40],
        iconAnchor: [28, 33],
      }),
      keyboard: false,
      interactive: false,
      zIndexOffset: 500,
      title: "You",
    }).addTo(map);
  }

  if (bounds.isValid()) {
    map.fitBounds(bounds, { padding: [28, 28], maxZoom: 15, animate: false });
  } else {
    map.setView([51.16, 10.45], 6);
  }

  node.addEventListener("focusin", () => map.scrollWheelZoom.enable());
  node.addEventListener("focusout", (event) => {
    if (!node.contains(event.relatedTarget)) {
      map.scrollWheelZoom.disable();
    }
  });

  const refit = () => map.invalidateSize();
  window.addEventListener("resize", refit);
  window.requestAnimationFrame(refit);
})();
