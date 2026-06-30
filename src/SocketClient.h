#pragma once
#include <string>
#include <memory>
#include <mutex>
#include <queue>
#include <array>
#include <atomic>
#include "Constants.h"
namespace ix { class WebSocket; }

class SocketClient {
    public:
        SocketClient(const std::string& url = "ws://localhost:5884");
        ~SocketClient();

        void connect();
        void disconnect();
        bool isConnected() const;
        void sendState(const std::string& j);
        bool pollIntent(PlayerIntent& out);
        std::array<int, 2> getTrainState();

    private:
        std::unique_ptr<ix::WebSocket> ws;
        std::queue<PlayerIntent> queue;
        std::array<int, 2> train_state = {0, 0};
        std::atomic<bool> config_received = false;
        const std::string url;
        std::mutex mutex;
        bool is_connected = false;
};