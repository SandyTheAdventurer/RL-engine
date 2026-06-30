#include <string>
#include <mutex>
#include <ixwebsocket/IXWebSocket.h>
#include <ixwebsocket/IXNetSystem.h>
#include <nlohmann/json.hpp>
#include <spdlog/spdlog.h>
#include "SocketClient.h"

using json = nlohmann::json;

SocketClient::SocketClient(const std::string& url)
:url(url), ws(std::make_unique<ix::WebSocket>()) {
    ix::initNetSystem();
}

SocketClient::~SocketClient() {
    disconnect();
    spdlog::info("Disconnection sent from client");
}

void SocketClient::connect() {
    ws->setUrl(url);
    ws->setOnMessageCallback([this](const ix::WebSocketMessagePtr& msg) {
        if(msg->type == ix::WebSocketMessageType::Open) {
            is_connected = true;
            spdlog::info("Connected to server at {}", url.c_str());
        }
        else if(msg->type == ix::WebSocketMessageType::Close) {
            is_connected = false;
            spdlog::info("Disconnedted from server: {}", msg->closeInfo.reason.c_str());
        }
        else if(msg->type == ix::WebSocketMessageType::Message) {
            try {
                json j = json::parse(msg->str);
                if(j.value("type", "intent") == "intent") {
                    PlayerIntent intent;
                    intent.mx = j.value("mx", 0.0f);
                    intent.my = j.value("my", 0.0f);
                    intent.fire = j.value("fire", false);
                    intent.aim_x = j.value("aim_x", 0.0f);
                    intent.aim_y = j.value("aim_y", 0.0f);
                    std::lock_guard<std::mutex> lock(mutex);
                    queue.push(intent);
                }
                else{
                    train_state = {j.value("data_iter", 5), j.value("train_iter", 100)};
                }
            }
            catch(json::parse_error) {spdlog::error("Error in parsing JSON response");}
        }
        else if(msg->type == ix::WebSocketMessageType::Error) {
            spdlog::error("Error: {}", msg->errorInfo.reason.c_str());
        }
    });

    ws->start();
}

void SocketClient::disconnect() {
    ws->stop();
    is_connected = false;
}

void SocketClient::sendState(const std::string& j) {
    if(is_connected) {
        ws->send(j);
    }
}

bool SocketClient::isConnected() const {
    return is_connected;
}

bool SocketClient::pollIntent(PlayerIntent& out){
    std::lock_guard<std::mutex> lock(mutex);
    if (queue.empty()) {return false;}
    out = queue.front();
    queue.pop();
    return true;
}

std::array<int, 2> SocketClient::getTrainState() {
    return train_state;
}