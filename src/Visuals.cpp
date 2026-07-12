#include "Visuals.h"
#include <SDL3_image/SDL_image.h>
#include <cmath>

TTF_Font* Visuals::font = nullptr;
SDL_Texture* Visuals::start_text = nullptr;
SDL_Texture* Visuals::train_text = nullptr;
SDL_Texture* Visuals::end_text = nullptr;
float Visuals::start_w = 0, Visuals::start_h = 0;
float Visuals::train_w = 0, Visuals::train_h = 0;
float Visuals::end_w = 0, Visuals::end_h = 0;
Button Visuals::play_btn = {};
Button Visuals::quit_btn = {};
Button Visuals::restart_btn = {};
Audio Visuals::audio;

static constexpr float btn_w = 220.0f;
static constexpr float btn_h = 50.0f;
static constexpr float btn_spacing = 20.0f;

static SDL_Color btn_bg       = {50, 50, 50, 255};
static SDL_Color btn_bg_hover = {90, 90, 90, 255};
static SDL_Color btn_border   = {180, 180, 180, 255};
static SDL_Color btn_text_c   = {220, 220, 220, 255};
static SDL_Color white = {255, 255, 255, 255};
static SDL_Color green = {100, 220, 100, 255};
static SDL_Color red   = {220, 80, 80, 255};
static SDL_Color grey  = {120, 120, 120, 255};
static SDL_Color yellow = {220, 220, 80, 255};

static constexpr float col1_x = 30.0f;
static constexpr float col1_w = 280.0f;
static constexpr float col2_x = 340.0f;
static constexpr float col2_w = 550.0f;
static constexpr float row_h = 22.0f;
static constexpr float btn_h_sm = 18.0f;

SDL_Texture* Visuals::make_text(SDL_Renderer* r, TTF_Font* f, const char* t, SDL_Color c) {
    SDL_Surface* s = TTF_RenderText_Blended(f, t, SDL_strlen(t), c);
    if (!s) return nullptr;
    SDL_Texture* tx = SDL_CreateTextureFromSurface(r, s);
    SDL_DestroySurface(s);
    return tx;
}

void Visuals::init(Engine& engine, Player& p1, Player& p2) {
    SDL_Renderer* r = engine.renderer;
    if (!r) return;

    audio.init(0.6f);
    audio.load_from_directory("assets/music");

    TTF_Init();
    font = TTF_OpenFont("assets/LiberationSans-Regular.ttf", font_size);
    if (!font) return;

    start_text = make_text(r, font, "RL ENGINE", white);
    train_text = make_text(r, font, "TRAINING HOW TO BEAT YOU...", white);
    end_text = make_text(r, font, "LEVEL UP", white);

    if (start_text) SDL_GetTextureSize(start_text, &start_w, &start_h);
    if (train_text) SDL_GetTextureSize(train_text, &train_w, &train_h);
    if (end_text)   SDL_GetTextureSize(end_text, &end_w, &end_h);

    make_buttons(r);
}

void Visuals::make_buttons(SDL_Renderer* r) {
    float cx = (screenw - btn_w) / 2.0f;
    float cy = 380.0f;

    play_btn.rect = {cx, cy, btn_w, btn_h};
    restart_btn.rect = {cx, cy, btn_w, btn_h};
    cy += btn_h + btn_spacing;
    quit_btn.rect = {cx, cy, btn_w, btn_h};

    SDL_Texture* t;

    t = make_text(r, font, "  [ PLAY ]  ", btn_text_c);
    if (t) { SDL_GetTextureSize(t, &play_btn.text_w, &play_btn.text_h); }
    play_btn.text = t;

    t = make_text(r, font, "  [ QUIT ]  ", btn_text_c);
    if (t) { SDL_GetTextureSize(t, &quit_btn.text_w, &quit_btn.text_h); }
    quit_btn.text = t;

    t = make_text(r, font, "  [ RESTART ]  ", btn_text_c);
    if (t) { SDL_GetTextureSize(t, &restart_btn.text_w, &restart_btn.text_h); }
    restart_btn.text = t;
}

bool Visuals::point_in_rect(float px, float py, SDL_FRect rect) {
    return px >= rect.x && px <= rect.x + rect.w &&
           py >= rect.y && py <= rect.y + rect.h;
}

void Visuals::draw_button(SDL_Renderer* r, Button& btn, float mx, float my) {
    bool hovered = point_in_rect(mx, my, btn.rect);
    SDL_Color bg = hovered ? btn_bg_hover : btn_bg;

    SDL_SetRenderDrawColor(r, bg.r, bg.g, bg.b, bg.a);
    SDL_RenderFillRect(r, &btn.rect);
    SDL_SetRenderDrawColor(r, btn_border.r, btn_border.g, btn_border.b, btn_border.a);
    SDL_RenderRect(r, &btn.rect);

    if (btn.text && btn.text_w > 0 && btn.text_h > 0) {
        SDL_FRect dst = {
            btn.rect.x + (btn.rect.w - btn.text_w) / 2.0f,
            btn.rect.y + (btn.rect.h - btn.text_h) / 2.0f,
            btn.text_w, btn.text_h
        };
        SDL_RenderTexture(r, btn.text, nullptr, &dst);
    }
}

static bool click_inside(float mx, float my, SDL_FRect r) {
    return mx >= r.x && mx <= r.x + r.w && my >= r.y && my <= r.y + r.h;
}




MenuResult Visuals::start_menu(Engine& engine, FrameInput& input) {
    SDL_Renderer* r = engine.renderer;
    if (!r) return MenuResult::NONE;
    SDL_SetRenderDrawColor(r, 0, 0, 0, 255);
    SDL_RenderClear(r);

    float mx, my;
    SDL_GetMouseState(&mx, &my);

    if (start_text) {
        SDL_FRect dst = {(screenw - start_w) / 2, (screenh - start_h) / 2 - 100, start_w, start_h};
        SDL_RenderTexture(r, start_text, nullptr, &dst);
    }
    draw_button(r, play_btn, mx, my);
    draw_button(r, quit_btn, mx, my);
    SDL_RenderPresent(r);

    if (input.mouse_left_clicked) {
        if (point_in_rect(input.mouse_x, input.mouse_y, play_btn.rect))
            return MenuResult::PLAY;
        if (point_in_rect(input.mouse_x, input.mouse_y, quit_btn.rect))
            return MenuResult::QUIT;
    }
    return MenuResult::NONE;
}

MenuResult Visuals::end_menu(Engine& engine, FrameInput& input) {
    SDL_Renderer* r = engine.renderer;
    if (!r) return MenuResult::NONE;

    Player& p = engine.player1();
    SDL_SetRenderDrawColor(r, 0, 0, 0, 255);
    SDL_RenderClear(r);

    float mx, my;
    SDL_GetMouseState(&mx, &my);

    if (end_text) {
        SDL_FRect dst = {(screenw - end_w) / 2, 20, end_w, end_h};
        SDL_RenderTexture(r, end_text, nullptr, &dst);
    }

    char dimes_buf[64];
    SDL_snprintf(dimes_buf, sizeof(dimes_buf), "DIMES: %.0f", p.dimes);
    SDL_Texture* dimes_t = make_text(r, font, dimes_buf, yellow);
    if (dimes_t) {
        float dw, dh;
        SDL_GetTextureSize(dimes_t, &dw, &dh);
        SDL_FRect dd = {screenw - dw - 20, 25, dw, dh};
        SDL_RenderTexture(r, dimes_t, nullptr, &dd);
        SDL_DestroyTexture(dimes_t);
    }

    auto label = [&](const char* text, float x, float y, SDL_Color c) -> float {
        SDL_Texture* t = make_text(r, font, text, c);
        if (!t) return 0;
        float tw, th;
        SDL_GetTextureSize(t, &tw, &th);
        SDL_FRect dst = {x, y, tw, th};
        SDL_RenderTexture(r, t, nullptr, &dst);
        SDL_DestroyTexture(t);
        return th;
    };

    auto small_btn = [&](const char* text, float x, float y, float w, bool hovered) -> SDL_FRect {
        SDL_FRect b = {x, y, w, btn_h_sm};
        SDL_Color bg = hovered ? btn_bg_hover : btn_bg;
        SDL_SetRenderDrawColor(r, bg.r, bg.g, bg.b, bg.a);
        SDL_RenderFillRect(r, &b);
        SDL_SetRenderDrawColor(r, btn_border.r, btn_border.g, btn_border.b, btn_border.a);
        SDL_RenderRect(r, &b);
        SDL_Texture* t = make_text(r, font, text, btn_text_c);
        if (t) {
            float tw, th;
            SDL_GetTextureSize(t, &tw, &th);
            float tx = x + (w - tw) / 2.0f;
            float ty = y + (btn_h_sm - th) / 2.0f;
            SDL_FRect td = {tx, ty, tw, th};
            SDL_RenderTexture(r, t, nullptr, &td);
            SDL_DestroyTexture(t);
        }
        return b;
    };

    // Right column: bottom restart/quit
    float btn_cy = screenh - btn_h - 10;
    float btn_cx = (screenw - btn_w) / 2.0f;
    SDL_FRect restart_r = {btn_cx - btn_w - 10, btn_cy, btn_w, btn_h};
    SDL_FRect quit_r = {btn_cx + btn_w + 10, btn_cy, btn_w, btn_h};

    draw_button_shape(r, restart_r, mx, my, "  [ RESTART ]  ");
    draw_button_shape(r, quit_r, mx, my, "  [ QUIT ]  ");

    // ---- LEFT COLUMN: STATS ----
    float col_y = 70.0f;
    label("--- STATS ---", col1_x, col_y, white); col_y += row_h + 4;

    float stat_cost_btns[5];
    SDL_FRect stat_rects[5];

    for (int i = 0; i < 5; ++i) {
        float val;
        const char* sname;
        switch (i) {
            case 0: val = p.stats.strength;  sname = "STR"; break;
            case 1: val = p.stats.vitality;   sname = "VIT"; break;
            case 2: val = p.stats.agility;    sname = "AGI"; break;
            case 3: val = p.stats.reasoning;  sname = "REA"; break;
            default: val = p.stats.endurance; sname = "END"; break;
        }
        float cost = UpgradeCosts::stat_cost(static_cast<int>(val));
        bool maxed = val >= max_stat_value;
        bool can_afford = p.can_afford(cost) && !maxed;

        char buf[64];
        if (maxed)
            SDL_snprintf(buf, sizeof(buf), "%s %.0f MAX", sname, val);
        else
            SDL_snprintf(buf, sizeof(buf), "%s %.0f", sname, val);

        label(buf, col1_x, col_y, white);

        if (!maxed) {
            char cost_buf[32];
            SDL_snprintf(cost_buf, sizeof(cost_buf), "[%d]", static_cast<int>(cost));
            SDL_Color c = can_afford ? green : grey;
            float cw = 50.0f;
            float cx = col1_x + col1_w - cw;
            bool hovered = click_inside(mx, my, {cx, col_y, cw, btn_h_sm});
            stat_rects[i] = small_btn(cost_buf, cx, col_y, cw, hovered && can_afford);
            stat_cost_btns[i] = cost;
        }
        col_y += row_h + 2;
    }

    // ---- LEFT COLUMN: ARMOR UPGRADES ----
    col_y += 8.0f;
    label("--- ARMOR ---", col1_x, col_y, white); col_y += row_h + 4;

    static const char* armor_names[3] = {"Head", "Chest", "Legs"};
    SDL_FRect armor_rects[3];
    for (int i = 0; i < 3; ++i) {
        int lv = p.armor_upgrade_levels[i];
        float cost = UpgradeCosts::armor_cost(lv);
        bool maxed = lv >= max_upgrade_level;
        bool can_afford = p.can_afford(cost) && !maxed;

        char buf[64];
        SDL_snprintf(buf, sizeof(buf), "%s Lv%d", armor_names[i], lv);
        label(buf, col1_x, col_y, white);

        if (!maxed) {
            char cost_buf[32];
            SDL_snprintf(cost_buf, sizeof(cost_buf), "[%d]", static_cast<int>(cost));
            float cw = 50.0f;
            float cx = col1_x + col1_w - cw;
            bool hovered = click_inside(mx, my, {cx, col_y, cw, btn_h_sm});
            armor_rects[i] = small_btn(cost_buf, cx, col_y, cw, hovered && can_afford);
        }
        col_y += row_h + 2;
    }

    // ---- RIGHT COLUMN: WEAPON SHOP (with per-weapon upgrades) ----
    float rcol_y = 70.0f;
    label("--- WEAPONS ---", col2_x, rcol_y, white); rcol_y += row_h + 4;

    SDL_FRect weapon_buy_rects[weapon_count];
    SDL_FRect weapon_equip_rects[weapon_count];
    SDL_FRect weapon_upgrade_rects[weapon_count];

    for (int i = 0; i < weapon_count; ++i) {
        WeaponType wt = static_cast<WeaponType>(i);
        const WeaponShopInfo& info = get_weapon_shop_info(wt);
        bool owned = p.owned_weapons[i];
        bool equipped = p.equipment.weapon == wt;
        int lv = p.weapon_upgrade_levels[i];

        char buf[64];
        if (owned && equipped)
            SDL_snprintf(buf, sizeof(buf), ">> %s Lv%d (eq)", info.name, lv);
        else if (owned)
            SDL_snprintf(buf, sizeof(buf), "   %s Lv%d", info.name, lv);
        else
            SDL_snprintf(buf, sizeof(buf), "   %s", info.name);

        SDL_Color c = equipped ? green : (owned ? white : grey);
        label(buf, col2_x, rcol_y, c);

        float bx = col2_x + col2_w;
        if (!owned) {
            char cost_buf[32];
            SDL_snprintf(cost_buf, sizeof(cost_buf), "[Buy %d]", static_cast<int>(info.cost));
            float bw = 70.0f;
            bx -= bw;
            bool can_afford_buy = p.can_afford(info.cost);
            bool hovered_buy = click_inside(mx, my, {bx, rcol_y, bw, btn_h_sm});
            weapon_buy_rects[i] = small_btn(cost_buf, bx, rcol_y, bw, hovered_buy && can_afford_buy);
        } else {
            bool maxed = lv >= max_upgrade_level;
            float cost = UpgradeCosts::weapon_cost(lv);
            bool can_afford_upg = p.can_afford(cost) && !maxed;
            if (!maxed) {
                char cost_buf[32];
                SDL_snprintf(cost_buf, sizeof(cost_buf), "[%d]", static_cast<int>(cost));
                float uw = 50.0f;
                bx -= uw;
                bool hovered_upg = click_inside(mx, my, {bx, rcol_y, uw, btn_h_sm});
                weapon_upgrade_rects[i] = small_btn(cost_buf, bx, rcol_y, uw, hovered_upg && can_afford_upg);
            }
        }
        if (owned && !equipped) {
            float bw = 55.0f;
            bx -= bw;
            bool hovered_equip = click_inside(mx, my, {bx, rcol_y, bw, btn_h_sm});
            weapon_equip_rects[i] = small_btn("[Equip]", bx, rcol_y, bw, hovered_equip);
        }
        rcol_y += row_h + 2;
    }

    SDL_RenderPresent(r);

    // ---- PROCESS CLICKS ----
    if (input.mouse_left_clicked) {
        float cx = input.mouse_x;
        float cy = input.mouse_y;

        if (click_inside(cx, cy, restart_r)) return MenuResult::RESTART;
        if (click_inside(cx, cy, quit_r)) return MenuResult::QUIT;

        for (int i = 0; i < 5; ++i) {
            if (click_inside(cx, cy, stat_rects[i])) {
                p.purchase_stat_upgrade(static_cast<StatType>(i));
                return MenuResult::NONE;
            }
        }

        for (int i = 0; i < 3; ++i) {
            if (click_inside(cx, cy, armor_rects[i])) {
                p.purchase_armor_upgrade(static_cast<ArmorSlot>(i));
                return MenuResult::NONE;
            }
        }

        for (int i = 0; i < weapon_count; ++i) {
            if (click_inside(cx, cy, weapon_buy_rects[i])) {
                if (p.purchase_weapon(static_cast<WeaponType>(i)))
                    engine.reload_weapon_texture(p);
                return MenuResult::NONE;
            }
            if (click_inside(cx, cy, weapon_equip_rects[i])) {
                if (p.equip_weapon(static_cast<WeaponType>(i)))
                    engine.reload_weapon_texture(p);
                return MenuResult::NONE;
            }
            if (click_inside(cx, cy, weapon_upgrade_rects[i])) {
                p.purchase_weapon_upgrade(i);
                return MenuResult::NONE;
            }
        }
    }

    return MenuResult::NONE;
}

void Visuals::draw_button_shape(SDL_Renderer* r, SDL_FRect rect, float mx, float my,
                                 const char* text) {
    bool hovered = click_inside(mx, my, rect);
    SDL_Color bg = hovered ? btn_bg_hover : btn_bg;
    SDL_SetRenderDrawColor(r, bg.r, bg.g, bg.b, bg.a);
    SDL_RenderFillRect(r, &rect);
    SDL_SetRenderDrawColor(r, btn_border.r, btn_border.g, btn_border.b, btn_border.a);
    SDL_RenderRect(r, &rect);

    SDL_Texture* t = make_text(r, font, text, btn_text_c);
    if (t) {
        float tw, th;
        SDL_GetTextureSize(t, &tw, &th);
        SDL_FRect dst = {
            rect.x + (rect.w - tw) / 2.0f,
            rect.y + (rect.h - th) / 2.0f,
            tw, th
        };
        SDL_RenderTexture(r, t, nullptr, &dst);
        SDL_DestroyTexture(t);
    }
}

void Visuals::hud(Engine& engine) {
    SDL_Renderer* r = engine.renderer;
    if (!r) return;

    Player& p1 = engine.player1();
    Player& p2 = engine.player2();

    // ---- PLAYER 1 HUD (TOP LEFT) ----
    float padding = 20.0f;
    float bar_w = 300.0f;
    float h_bar = 24.0f;
    float s_bar = 14.0f;
    float gap = 4.0f;
    
    float current_y = padding;
    
    // HP
    SDL_FRect hp_bg = {padding, current_y, bar_w, h_bar};
    SDL_SetRenderDrawColor(r, 40, 40, 40, 200);
    SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_BLEND);
    SDL_RenderFillRect(r, &hp_bg);
    
    float hp_frac = p1.health / p1.max_hp;
    if (hp_frac > 0.0f) {
        SDL_FRect hp_fill = {padding + 2, current_y + 2, (bar_w - 4) * hp_frac, h_bar - 4};
        SDL_SetRenderDrawColor(r, 220, 40, 40, 255);
        SDL_RenderFillRect(r, &hp_fill);
    }
    SDL_SetRenderDrawColor(r, 180, 180, 180, 255);
    SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_NONE);
    SDL_RenderRect(r, &hp_bg);
    
    char hp_buf[32];
    SDL_snprintf(hp_buf, sizeof(hp_buf), "%.0f / %.0f", p1.health, p1.max_hp);
    SDL_Texture* hp_t = make_text(r, font, hp_buf, white);
    if (hp_t) {
        float hw, hh;
        SDL_GetTextureSize(hp_t, &hw, &hh);
        SDL_FRect hd = {padding + (bar_w - hw) / 2.0f, current_y + (h_bar - hh) / 2.0f, hw, hh};
        SDL_RenderTexture(r, hp_t, nullptr, &hd);
        SDL_DestroyTexture(hp_t);
    }

    if (p1.damage_flash > 0.0f) {
        char dmg_buf[32];
        SDL_snprintf(dmg_buf, sizeof(dmg_buf), "%.0f", p1.damage_taken);
        uint8_t alpha = static_cast<uint8_t>((p1.damage_flash / 1.5f) * 255);
        SDL_Color dmg_c = {200, 30, 30, alpha};
        SDL_Texture* dmg_t = make_text(r, font, dmg_buf, dmg_c);
        if (dmg_t) {
            float dw, dh;
            SDL_GetTextureSize(dmg_t, &dw, &dh);
            SDL_FRect dd = {padding + bar_w + 10.0f, current_y, dw, dh};
            SDL_RenderTexture(r, dmg_t, nullptr, &dd);
            SDL_DestroyTexture(dmg_t);
        }
    }
    
    current_y += h_bar + gap;
    
    // Stamina
    SDL_FRect sp_bg = {padding, current_y, bar_w * 0.8f, s_bar};
    SDL_SetRenderDrawColor(r, 40, 40, 40, 200);
    SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_BLEND);
    SDL_RenderFillRect(r, &sp_bg);
    
    float sp_frac = p1.stamina.current / p1.stamina.max_stamina;
    if (sp_frac > 0.0f) {
        SDL_FRect sp_fill = {padding + 2, current_y + 2, (bar_w * 0.8f - 4) * sp_frac, s_bar - 4};
        SDL_SetRenderDrawColor(r, 60, 180, 240, 255);
        SDL_RenderFillRect(r, &sp_fill);
    }
    SDL_SetRenderDrawColor(r, 180, 180, 180, 255);
    SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_NONE);
    SDL_RenderRect(r, &sp_bg);
    
    current_y += s_bar + gap;
    
    // Mana
    SDL_FRect mp_bg = {padding, current_y, bar_w * 0.6f, s_bar};
    SDL_SetRenderDrawColor(r, 40, 40, 40, 200);
    SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_BLEND);
    SDL_RenderFillRect(r, &mp_bg);
    
    float mp_frac = p1.mana / p1.max_mana;
    if (mp_frac > 0.0f) {
        SDL_FRect mp_fill = {padding + 2, current_y + 2, (bar_w * 0.6f - 4) * mp_frac, s_bar - 4};
        SDL_SetRenderDrawColor(r, 160, 60, 240, 255);
        SDL_RenderFillRect(r, &mp_fill);
    }
    SDL_SetRenderDrawColor(r, 180, 180, 180, 255);
    SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_NONE);
    SDL_RenderRect(r, &mp_bg);

    // Dimes UI
    char dimes_buf[32];
    SDL_snprintf(dimes_buf, sizeof(dimes_buf), "DIMES: %.0f", p1.dimes);
    SDL_Texture* dimes_t = make_text(r, font, dimes_buf, yellow);
    if (dimes_t) {
        float dw, dh;
        SDL_GetTextureSize(dimes_t, &dw, &dh);
        SDL_FRect dd = {padding, current_y + s_bar + 10.0f, dw, dh};
        SDL_RenderTexture(r, dimes_t, nullptr, &dd);
        SDL_DestroyTexture(dimes_t);
    }

    // Draw dropped dimes if present
    DroppedDimes& drop = engine.get_drop();
    if (!drop.collected && drop.amount > 0.0f) {
        float cur = drop.current_amount();
        if (cur > 0.0f) {
            char drop_buf[64];
            SDL_snprintf(drop_buf, sizeof(drop_buf), "D:%.0f", cur);
            SDL_Texture* dt = make_text(r, font, drop_buf, yellow);
            if (dt) {
                float dw, dh;
                SDL_GetTextureSize(dt, &dw, &dh);
                SDL_FRect dd = {drop.x, drop.y - 20.0f, dw, dh};
                SDL_RenderTexture(r, dt, nullptr, &dd);
                SDL_DestroyTexture(dt);
            }

            SDL_SetRenderDrawColor(r, 255, 215, 0, 200);
            SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_BLEND);
            SDL_FRect dp = {drop.x - 8, drop.y - 8, 16, 16};
            SDL_RenderFillRect(r, &dp);
            SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_NONE);
        }
    }

    // ---- PLAYER 2 (BOSS) HUD (BOTTOM CENTER) ----
    float p2_bar_w = 600.0f;
    float p2_bar_h = 24.0f;
    float p2_bar_x = (screenw - p2_bar_w) / 2.0f;
    float p2_bar_y = screenh - 60.0f;

    SDL_Texture* name_t = make_text(r, font, p2.getName().c_str(), white);
    if (name_t) {
        float nw, nh;
        SDL_GetTextureSize(name_t, &nw, &nh);
        float name_y = p2_bar_y - nh - 6;
        SDL_FRect dst = {(screenw - nw) / 2.0f, name_y, nw, nh};
        SDL_RenderTexture(r, name_t, nullptr, &dst);
        SDL_DestroyTexture(name_t);
    }

    if (p2.damage_flash > 0.0f) {
        char dmg_buf[32];
        SDL_snprintf(dmg_buf, sizeof(dmg_buf), "%.0f", p2.damage_taken);
        uint8_t alpha = static_cast<uint8_t>((p2.damage_flash / 1.5f) * 255);
        SDL_Color dmg_c = {200, 30, 30, alpha};
        SDL_Texture* dmg_t = make_text(r, font, dmg_buf, dmg_c);
        if (dmg_t) {
            float dw, dh;
            SDL_GetTextureSize(dmg_t, &dw, &dh);
            float name_y = p2_bar_y - 6;
            SDL_FRect dd = {(screenw - dw) / 2.0f, name_y - dh - 6, dw, dh};
            SDL_RenderTexture(r, dmg_t, nullptr, &dd);
            SDL_DestroyTexture(dmg_t);
        }
    }

    SDL_SetRenderDrawColor(r, 40, 40, 40, 200);
    SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_BLEND);
    SDL_FRect p2_bg = {p2_bar_x, p2_bar_y, p2_bar_w, p2_bar_h};
    SDL_RenderFillRect(r, &p2_bg);

    float p2_hp_frac = p2.health / p2.max_hp;
    if (p2_hp_frac > 0.0f) {
        SDL_SetRenderDrawColor(r, 220, 40, 40, 255);
        SDL_FRect p2_fill = {p2_bar_x + 2, p2_bar_y + 2, (p2_bar_w - 4) * p2_hp_frac, p2_bar_h - 4};
        SDL_RenderFillRect(r, &p2_fill);
    }

    SDL_SetRenderDrawColor(r, 180, 180, 180, 255);
    SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_NONE);
    SDL_RenderRect(r, &p2_bg);

    char p2_hp_buf[32];
    SDL_snprintf(p2_hp_buf, sizeof(p2_hp_buf), "%.0f / %.0f", p2.health, p2.max_hp);
    SDL_Texture* p2_hp_t = make_text(r, font, p2_hp_buf, white);
    if (p2_hp_t) {
        float hw, hh;
        SDL_GetTextureSize(p2_hp_t, &hw, &hh);
        SDL_FRect hd = {(screenw - hw) / 2.0f, p2_bar_y + (p2_bar_h - hh) / 2.0f, hw, hh};
        SDL_RenderTexture(r, p2_hp_t, nullptr, &hd);
        SDL_DestroyTexture(p2_hp_t);
    }

    auto draw_badges = [&](Player& p) {
        float cx = p.box.x + p.box.w / 2.0f;
        float cy = p.box.y - 15.0f;
        auto draw_badge = [&](const char* text, SDL_Color c) {
            SDL_Texture* t = make_text(r, font, text, c);
            if (t) {
                float tw, th;
                SDL_GetTextureSize(t, &tw, &th);
                SDL_FRect dst = {cx - tw/2.0f, cy - th, tw, th};
                SDL_RenderTexture(r, t, nullptr, &dst);
                SDL_DestroyTexture(t);
                cy -= (th + 2.0f);
            }
        };
        if (p.stun_timer > 0.0f) draw_badge("STUN", {255, 255, 0, 255});
        if (p.slow_timer > 0.0f) draw_badge("SLOW", {0, 255, 255, 255});
    };
    draw_badges(p1);
    draw_badges(p2);
}

void Visuals::start_fight_music() {
    audio.play_random();
}

void Visuals::stop_fight_music() {
    audio.stop();
}

void Visuals::shutdown() {
    audio.shutdown();
    if (font) TTF_CloseFont(font);
    if (start_text) SDL_DestroyTexture(start_text);
    if (train_text) SDL_DestroyTexture(train_text);
    if (end_text) SDL_DestroyTexture(end_text);
    if (play_btn.text) SDL_DestroyTexture(play_btn.text);
    if (quit_btn.text) SDL_DestroyTexture(quit_btn.text);
    if (restart_btn.text) SDL_DestroyTexture(restart_btn.text);
    TTF_Quit();
}
