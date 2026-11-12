/**
 * realtime.js - Shared resilient WebSocket client for Events Booking
 * Connects event detail pages, live stage rooms, and gate check-in monitors
 * to FastAPI native WebSocket streams (/ws/events/{id}, /ws/live/{id}, /ws/telemetry).
 */
(function (global) {
    function buildWsUrl(path) {
        const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${proto}//${window.location.host}${path}`;
    }

    function connectWebSocket(path, onMessage, options) {
        if (!('WebSocket' in window)) return null;
        const opts = options || {};
        let attempt = 0;
        let ws = null;
        let closedManually = false;
        let pingTimer = null;

        function open() {
            if (closedManually) return;
            try {
                ws = new WebSocket(buildWsUrl(path));
            } catch (err) {
                scheduleReconnect();
                return;
            }
            ws.onopen = function () {
                attempt = 0;
                if (opts.onStatus) opts.onStatus('connected');
                if (pingTimer) clearInterval(pingTimer);
                pingTimer = setInterval(function () {
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        ws.send('ping');
                    }
                }, 25000);
            };
            ws.onmessage = function (evt) {
                if (evt.data === 'pong') return;
                try {
                    const data = JSON.parse(evt.data);
                    if (onMessage) onMessage(data, ws);
                } catch (_) {}
            };
            ws.onclose = function () {
                if (pingTimer) clearInterval(pingTimer);
                if (opts.onStatus) opts.onStatus('reconnecting');
                if (!closedManually) scheduleReconnect();
            };
            ws.onerror = function () {
                if (ws) ws.close();
            };
        }

        function scheduleReconnect() {
            const delay = Math.min(15000, 1000 * Math.pow(1.6, attempt++));
            setTimeout(open, delay);
        }

        open();
        return {
            send: function (obj) {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(typeof obj === 'string' ? obj : JSON.stringify(obj));
                }
            },
            close: function () {
                closedManually = true;
                if (pingTimer) clearInterval(pingTimer);
                if (ws) ws.close();
            }
        };
    }

    global.EventsRealtime = {
        connectEventSeats: function (eventId, onUpdate, onStatus) {
            return connectWebSocket(`/ws/events/${eventId}`, onUpdate, { onStatus });
        },
        connectLiveStage: function (eventId, onEvent, onStatus) {
            return connectWebSocket(`/ws/live/${eventId}`, onEvent, { onStatus });
        },
        connectTelemetry: function (onEvent, onStatus) {
            return connectWebSocket('/ws/telemetry', onEvent, { onStatus });
        }
    };
})(window);

