import customtkinter as ctk
from utils import database as db

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class EyeMouseUI(ctk.CTk):
    def __init__(self, start_cmd, stop_cmd, calib_cmd, exit_cmd, saved_ip=""):
        super().__init__()
        self.title("EyePilot: A Computer Vision-Based Virtual Mouse System")
        self.geometry("1300x840")
        self.minsize(1200, 780)
        self.configure(fg_color="#EDF2F7")

        self.start_cmd = start_cmd
        self.stop_cmd = stop_cmd
        self.calib_cmd = calib_cmd
        self.exit_cmd = exit_cmd
        self.saved_ip = saved_ip

        self.badges = {}
        self.settings_window = None
        self.about_window = None
        self.ip_history_window = None
        
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.exit_cmd)

    def _build_ui(self):
        sidebar = ctk.CTkFrame(self, width=170, corner_radius=0, fg_color="#182A4A")
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.pack(pady=(25, 30), padx=15, anchor="w")
        ctk.CTkLabel(brand, text="👁", font=("Segoe UI Emoji", 20)).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(brand, text="EyeMouse", font=("Helvetica", 16, "bold"), text_color="#FFFFFF").pack(side="left")

        # Sidebar Buttons with Commands linked
        ctk.CTkButton(sidebar, text="  🏠  Home", anchor="w", fg_color="#243C66", text_color="#FFFFFF",
                      font=("Helvetica", 13, "bold"), height=40, corner_radius=8).pack(fill="x", padx=12, pady=4)
        
        ctk.CTkButton(sidebar, text="  ⚙️  Settings", anchor="w", fg_color="transparent", text_color="#A0AEC0", hover_color="#243C66",
                      font=("Helvetica", 13), height=40, corner_radius=8, command=self.show_settings).pack(fill="x", padx=12, pady=4)
        
        ctk.CTkButton(sidebar, text="🗄️ IP Database", anchor="w", fg_color="transparent", text_color="#A0AEC0", hover_color="#243C66",
                      font=("Helvetica", 13), height=40, corner_radius=8, command=self.show_ip_history).pack(fill="x", padx=12, pady=4)

        ctk.CTkButton(sidebar, text="  ℹ️  About", anchor="w", fg_color="transparent", text_color="#A0AEC0", hover_color="#243C66",
                      font=("Helvetica", 13), height=40, corner_radius=8, command=self.show_about).pack(fill="x", padx=12, pady=4)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(side="right", fill="both", expand=True, padx=20, pady=16)

        top_row = ctk.CTkFrame(content, fg_color="transparent", height=490)
        top_row.pack(fill="x", pady=(0, 14))
        top_row.pack_propagate(False)

        self.video_container = ctk.CTkFrame(top_row, corner_radius=14, fg_color="#1F2937")
        self.video_container.pack(side="left", fill="both", expand=True, padx=(0, 16))
        self.video_container.pack_propagate(False)

        self.lbl_camera_badge = ctk.CTkLabel(self.video_container, text="● Camera OFF", fg_color="#374151",
                                             text_color="#9CA3AF", corner_radius=12, font=("Helvetica", 11, "bold"),
                                             width=110, height=26)
        self.lbl_camera_badge.place(x=16, y=16)

        self.video_display = ctk.CTkLabel(self.video_container, text="")
        self.video_display.place(relx=0.5, rely=0.5, anchor="center")

        status_panel = ctk.CTkFrame(top_row, width=350, corner_radius=14, fg_color="#FFFFFF")
        status_panel.pack(side="right", fill="y")
        status_panel.pack_propagate(False)

        hdr = ctk.CTkFrame(status_panel, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(16, 8))
        ctk.CTkLabel(hdr, text="⚡", font=("Segoe UI Emoji", 16)).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(hdr, text="System Status", font=("Helvetica", 16, "bold"), text_color="#1E293B").pack(side="left")

        self._add_badge(status_panel, "camera", "📷", "Camera", "Inactive", "red")
        self._add_badge(status_panel, "face", "🔍", "Face Lock", "Searching...", "neutral")
        self._add_badge(status_panel, "left_eye", "👁️", "Left Eye", "Unknown", "neutral")
        self._add_badge(status_panel, "right_eye", "👁️", "Right Eye", "Unknown", "neutral")
        self._add_badge(status_panel, "cursor", "🖱️", "Cursor Control", "Disabled", "red")
        self._add_badge(status_panel, "click_action", "⚡", "Last Action", "None", "neutral")
        self._add_badge(status_panel, "mouth", "👄", "Mouth Status", "Closed", "neutral")
        self._add_badge(status_panel, "mode", "🎯", "Current Mode", "Paused", "neutral")

        bottom_row = ctk.CTkFrame(content, height=260, fg_color="transparent")
        bottom_row.pack(fill="x")
        bottom_row.pack_propagate(False)

        gestures_panel = ctk.CTkFrame(bottom_row, corner_radius=14, fg_color="#FFFFFF")
        gestures_panel.pack(side="left", fill="both", expand=True, padx=(0, 16))

        g_hdr = ctk.CTkFrame(gestures_panel, fg_color="transparent")
        g_hdr.pack(fill="x", padx=20, pady=(8, 4))
        ctk.CTkLabel(g_hdr, text="👃", font=("Segoe UI Emoji", 14)).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(g_hdr, text="Nose, Eye & Mouth Controls", font=("Helvetica", 14, "bold"), text_color="#1E293B").pack(side="left")

        cards = ctk.CTkFrame(gestures_panel, fg_color="transparent")
        cards.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self._build_card(cards, "👃", "Nose Movement", "Glide Cursor", "#EBF5FF")
        self._build_card(cards, "😉", "L/R Wink", "Left/Right Click", "#EFF6FF")
        self._build_card(cards, "😁", "Wide Smile", "Drag & Drop", "#EEF2FF")
        self._build_card(cards, "😴", "Long Blink", "Toggle Scroll", "#FAF5FF")
        self._build_card(cards, "👄", "Mouth Open", "Pause System", "#FDF2F8")

        ctrl_panel = ctk.CTkFrame(bottom_row, width=350, corner_radius=14, fg_color="#FFFFFF")
        ctrl_panel.pack(side="right", fill="y")
        ctrl_panel.pack_propagate(False)

        c_hdr = ctk.CTkFrame(ctrl_panel, fg_color="transparent")
        c_hdr.pack(fill="x", padx=20, pady=(8, 6))
        ctk.CTkLabel(c_hdr, text="🎛️", font=("Segoe UI Emoji", 14)).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(c_hdr, text="Control Panel", font=("Helvetica", 14, "bold"), text_color="#1E293B").pack(side="left")
        
        self.cam_selector = ctk.CTkOptionMenu(
            ctrl_panel, 
            values=[
                "Laptop Camera", 
                "DroidCam (Wi-Fi / IP)", 
                "DroidCam (USB Client - Cam 1)", 
                "External USB (Cam 2)"
            ], 
            fg_color="#3B82F6", 
            font=("Helvetica", 12, "bold"), 
            height=32
        )
        self.cam_selector.pack(fill="x", padx=16, pady=(0, 4))
        
        # DroidCam IP Input with SQLite History Selector
        ip_row = ctk.CTkFrame(ctrl_panel, fg_color="transparent")
        ip_row.pack(fill="x", padx=16, pady=(4, 4))

        db_recent = db.get_recent_ips()
        combo_vals = db_recent if db_recent else ([self.saved_ip] if self.saved_ip else ["10.69.68.61:4747"])

        self.ip_combo = ctk.CTkComboBox(
            ip_row,
            values=combo_vals,
            font=("Helvetica", 12),
            dropdown_font=("Helvetica", 11),
            height=32
        )
        self.ip_combo.pack(side="left", fill="x", expand=True, padx=(0, 6))
        if self.saved_ip:
            self.ip_combo.set(self.saved_ip)
        elif combo_vals:
            self.ip_combo.set(combo_vals[0])

        self.ip_entry = self.ip_combo  # Backward compatibility alias

        self.btn_ip_db = ctk.CTkButton(
            ip_row,
            text="🗄️",
            width=36,
            height=32,
            fg_color="#334155",
            hover_color="#1E293B",
            font=("Segoe UI Emoji", 14),
            corner_radius=6,
            command=self.show_ip_history
        )
        self.btn_ip_db.pack(side="right")

        self.mirror_var = ctk.BooleanVar(value=True)
        self.chk_mirror = ctk.CTkCheckBox(ctrl_panel, text="🪞 Mirror Video (Fix Reversed)", variable=self.mirror_var, font=("Helvetica", 12, "bold"))
        self.chk_mirror.pack(fill="x", padx=16, pady=(4, 6))

        btn_box = ctk.CTkFrame(ctrl_panel, fg_color="transparent")
        btn_box.pack(fill="x", padx=16, pady=(0, 4))
        self.btn_start = ctk.CTkButton(btn_box, text="▶  Start", fg_color="#22C55E", hover_color="#16A34A",
                                       font=("Helvetica", 13, "bold"), height=36, corner_radius=8, command=self.start_cmd)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_stop = ctk.CTkButton(btn_box, text="⏹  Stop", fg_color="#EF4444", hover_color="#DC2626",
                                      font=("Helvetica", 13, "bold"), height=36, corner_radius=8, command=self.stop_cmd)
        self.btn_stop.pack(side="right", fill="x", expand=True, padx=(5, 0))

        self.btn_calib = ctk.CTkButton(ctrl_panel, text="🎯  Recalibrate Center", fg_color="#3B82F6", hover_color="#2563EB",
                                       font=("Helvetica", 12, "bold"), height=30, corner_radius=8, command=self.calib_cmd)
        self.btn_calib.pack(fill="x", padx=16, pady=(0, 4))

    # --- POPUP WINDOWS ---
    def show_settings(self):
        """Displays a polished settings configuration window."""
        if self.settings_window is None or not self.settings_window.winfo_exists():
            self.settings_window = ctk.CTkToplevel(self)
            self.settings_window.title("System Settings")
            self.settings_window.geometry("400x350")
            self.settings_window.attributes("-topmost", True)
            self.settings_window.configure(fg_color="#FFFFFF")
            
            ctk.CTkLabel(self.settings_window, text="⚙️ Configuration Parameters", font=("Helvetica", 16, "bold")).pack(pady=(20, 15))
            
            # Cursor Speed Slider
            ctk.CTkLabel(self.settings_window, text="Cursor Tracking Speed", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=30)
            ctk.CTkSlider(self.settings_window, from_=1.0, to=5.0, number_of_steps=40).pack(fill="x", padx=30, pady=(0, 15))
            
            # Drag Sensitivity Slider
            ctk.CTkLabel(self.settings_window, text="Smile Sensitivity (Drag & Drop)", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=30)
            ctk.CTkSlider(self.settings_window, from_=0.01, to=0.1, number_of_steps=20).pack(fill="x", padx=30, pady=(0, 15))

            # Scroll Sensitivity Slider
            ctk.CTkLabel(self.settings_window, text="Blink Hold Duration (Scroll)", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=30)
            ctk.CTkSlider(self.settings_window, from_=0.3, to=1.0, number_of_steps=10).pack(fill="x", padx=30, pady=(0, 20))

            ctk.CTkButton(self.settings_window, text="Save & Apply", fg_color="#3B82F6", command=self.settings_window.destroy).pack(pady=10)
        else:
            self.settings_window.focus()

    def show_ip_history(self):
        """Displays SQLite Database History for DroidCam IP connections."""
        if self.ip_history_window is not None and self.ip_history_window.winfo_exists():
            self.ip_history_window.focus()
            return

        self.ip_history_window = ctk.CTkToplevel(self)
        self.ip_history_window.title("DroidCam Connection Database")
        self.ip_history_window.geometry("620x540")
        self.ip_history_window.minsize(540, 440)
        self.ip_history_window.attributes("-topmost", True)
        self.ip_history_window.configure(fg_color="#F8FAFC")

        # Header
        hdr_frame = ctk.CTkFrame(self.ip_history_window, fg_color="#182A4A", corner_radius=10)
        hdr_frame.pack(fill="x", padx=16, pady=(16, 10))
        
        h_box = ctk.CTkFrame(hdr_frame, fg_color="transparent")
        h_box.pack(padx=16, pady=12, fill="x")
        ctk.CTkLabel(h_box, text="🗄️", font=("Segoe UI Emoji", 24)).pack(side="left", padx=(0, 10))
        text_box = ctk.CTkFrame(h_box, fg_color="transparent")
        text_box.pack(side="left")
        ctk.CTkLabel(text_box, text="DroidCam IP Connection Database", font=("Helvetica", 15, "bold"), text_color="#FFFFFF").pack(anchor="w")

        # Action Toolbar
        action_bar = ctk.CTkFrame(self.ip_history_window, fg_color="transparent")
        action_bar.pack(fill="x", padx=16, pady=(0, 8))

        lbl_count = ctk.CTkLabel(action_bar, text="", font=("Helvetica", 11, "bold"), text_color="#475569")
        lbl_count.pack(side="left")

        # Scrollable container
        scroll_frame = ctk.CTkScrollableFrame(self.ip_history_window, fg_color="#FFFFFF", corner_radius=10)
        scroll_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        def render_records():
            for widget in scroll_frame.winfo_children():
                widget.destroy()

            records = db.get_all_history()
            lbl_count.configure(text=f"Total Records: {len(records)}")

            if not records:
                empty_box = ctk.CTkFrame(scroll_frame, fg_color="transparent")
                empty_box.pack(expand=True, pady=60)
                ctk.CTkLabel(empty_box, text="📂", font=("Segoe UI Emoji", 32)).pack(pady=(0, 8))
                ctk.CTkLabel(
                    empty_box,
                    text="No connection records in database.\nConnect to DroidCam to automatically log IP connections.",
                    font=("Helvetica", 11),
                    text_color="#94A3B8",
                    justify="center"
                ).pack()
                return

            for rec in records:
                rec_id = rec["id"]
                ip_val = rec["ip_address"]
                time_val = rec["connected_at"]
                status_val = rec.get("status", "Connected")
                notes_val = rec.get("notes", "")

                card = ctk.CTkFrame(scroll_frame, fg_color="#F8FAFC", corner_radius=8, border_width=1, border_color="#E2E8F0")
                card.pack(fill="x", pady=4, padx=4)

                # Info Left
                info_col = ctk.CTkFrame(card, fg_color="transparent")
                info_col.pack(side="left", padx=12, pady=8)

                ctk.CTkLabel(info_col, text=f"🌐 {ip_val}", font=("Helvetica", 12, "bold"), text_color="#0F172A").pack(anchor="w")
                
                detail_txt = f"{time_val}"
                if notes_val:
                    detail_txt += f"  •  {notes_val}"
                ctk.CTkLabel(info_col, text=detail_txt, font=("Helvetica", 10), text_color="#64748B").pack(anchor="w")

                # Right actions
                actions_col = ctk.CTkFrame(card, fg_color="transparent")
                actions_col.pack(side="right", padx=12, pady=8)

                # Status Badge
                badge_color = "#DCFCE7" if status_val in ("Connected", "Success") else ("#FEE2E2" if status_val == "Failed" else "#E0F2FE")
                badge_fg = "#15803D" if status_val in ("Connected", "Success") else ("#B91C1C" if status_val == "Failed" else "#0369A1")
                stat_badge = ctk.CTkLabel(
                    actions_col, text=status_val, fg_color=badge_color, text_color=badge_fg,
                    font=("Helvetica", 10, "bold"), corner_radius=6, width=74, height=22
                )
                stat_badge.pack(side="left", padx=(0, 8))

                def make_use_cmd(target_ip):
                    def _use():
                        self.set_ip_input(target_ip)
                        if self.ip_history_window and self.ip_history_window.winfo_exists():
                            self.ip_history_window.destroy()
                    return _use

                def make_del_cmd(target_id):
                    def _delete():
                        db.delete_record(target_id)
                        self.refresh_ip_list()
                        render_records()
                    return _delete

                ctk.CTkButton(
                    actions_col, text="Use IP", fg_color="#3B82F6", hover_color="#2563EB",
                    font=("Helvetica", 11, "bold"), width=60, height=24, corner_radius=5,
                    command=make_use_cmd(ip_val)
                ).pack(side="left", padx=(0, 6))

                ctk.CTkButton(
                    actions_col, text="✕", fg_color="#E2E8F0", hover_color="#CBD5E1",
                    text_color="#475569", font=("Helvetica", 11, "bold"), width=28, height=24, corner_radius=5,
                    command=make_del_cmd(rec_id)
                ).pack(side="left")

        def on_clear_all():
            db.clear_history()
            self.refresh_ip_list()
            render_records()

        btn_clear = ctk.CTkButton(
            action_bar, text="🗑️ Clear All", fg_color="#EF4444", hover_color="#DC2626",
            font=("Helvetica", 11, "bold"), width=90, height=26, corner_radius=6,
            command=on_clear_all
        )
        btn_clear.pack(side="right")

        render_records()

        # Bottom Close button
        ctk.CTkButton(
            self.ip_history_window, text="Close", fg_color="#64748B", hover_color="#475569",
            font=("Helvetica", 12, "bold"), height=34, corner_radius=8,
            command=self.ip_history_window.destroy
        ).pack(fill="x", padx=16, pady=(0, 14))

    def show_about(self):
        """Displays academic project details and comprehensive documentation."""
        if self.about_window is not None and self.about_window.winfo_exists():
            self.about_window.focus()
            return

        self.about_window = ctk.CTkToplevel(self)
        self.about_window.title("About Project - Eye & Mouth Controlled Virtual Mouse")
        self.about_window.geometry("700x640")
        self.about_window.minsize(640, 580)
        self.about_window.attributes("-topmost", True)
        self.about_window.configure(fg_color="#F8FAFC")

        # Top Hero Banner
        banner = ctk.CTkFrame(self.about_window, fg_color="#182A4A", corner_radius=12)
        banner.pack(fill="x", padx=18, pady=(16, 10))

        b_content = ctk.CTkFrame(banner, fg_color="transparent")
        b_content.pack(padx=20, pady=16, fill="x")

        ctk.CTkLabel(b_content, text="👁️", font=("Segoe UI Emoji", 26)).pack(side="left", padx=(0, 12))
        b_text = ctk.CTkFrame(b_content, fg_color="transparent")
        b_text.pack(side="left")
        ctk.CTkLabel(b_text, text="EyePilot: A Computer Vision-Based Virtual Mouse", font=("Helvetica", 16, "bold"), text_color="#FFFFFF").pack(anchor="w")
        ctk.CTkLabel(b_text, text="Assistive AI Computer Vision Interface ", font=("Helvetica", 11), text_color="#94A3B8").pack(anchor="w")

        # Tabview
        tabview = ctk.CTkTabview(self.about_window, fg_color="#FFFFFF", corner_radius=10)
        tabview.pack(fill="both", expand=True, padx=18, pady=(0, 12))

        tab_overview = tabview.add("📋 Overview")
        tab_gestures = tabview.add("🕹️ Gestures")
        tab_arch = tabview.add("⚙️ Architecture")
        tab_academic = tabview.add("🎓 Academic Details")

        # --- TAB 1: OVERVIEW ---
        f_ov = ctk.CTkScrollableFrame(tab_overview, fg_color="transparent")
        f_ov.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(f_ov, text="Project Motivation & Problem Statement", font=("Helvetica", 13, "bold"), text_color="#1E293B").pack(anchor="w", pady=(4, 6))
        desc_text = (
            "This project provides a completely hands-free human-computer interaction system "
            "engineered for individuals suffering from severe upper-limb motor impairments, quadriplegia, "
            "cerebral palsy, or ALS. By replacing physical mouse and touch input with real-time biometric "
            "facial tracking, users can seamlessly navigate their operating system, interact with digital "
            "workstations, browse the web, and execute fine mouse actions purely through facial movements."
        )
        ctk.CTkLabel(f_ov, text=desc_text, font=("Helvetica", 11), text_color="#475569", justify="left", wraplength=580).pack(anchor="w", pady=(0, 12))

        ctk.CTkLabel(f_ov, text="Key Capabilities & Innovations", font=("Helvetica", 13, "bold"), text_color="#1E293B").pack(anchor="w", pady=(6, 6))
        
        def _add_feature(parent, icon, title, text):
            box = ctk.CTkFrame(parent, fg_color="#F1F5F9", corner_radius=8)
            box.pack(fill="x", pady=4)
            r = ctk.CTkFrame(box, fg_color="transparent")
            r.pack(fill="x", padx=12, pady=8)
            ctk.CTkLabel(r, text=icon, font=("Segoe UI Emoji", 16)).pack(side="left", padx=(0, 10))
            t = ctk.CTkFrame(r, fg_color="transparent")
            t.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(t, text=title, font=("Helvetica", 11, "bold"), text_color="#0F172A").pack(anchor="w")
            ctk.CTkLabel(t, text=text, font=("Helvetica", 10), text_color="#64748B", justify="left", wraplength=480).pack(anchor="w")

        _add_feature(f_ov, "⚡", "Sub-Pixel 1-Euro Adaptive Filtering", "Eliminates high-frequency micro-tremors and natural head jitters while preserving high-speed pointer responsiveness.")
        _add_feature(f_ov, "👁️", "Biometric EAR Wink Recognition", "Precise Eye Aspect Ratio (EAR) isolates single-eye winks for left and right mouse clicks without mistaking involuntary blinks.")
        _add_feature(f_ov, "👄", "Mouth-Driven Drag & Pause Safety", "Mouth Aspect Ratio (MAR) triggers mouse click-and-drag via smile detection and toggles system pause with mouth open.")
        _add_feature(f_ov, "📱", "DroidCam Wireless Connectivity & Database", "Full support for smartphone cameras over Wi-Fi, backed by a persistent SQLite database for instant IP reconnection and history tracking.")

        # --- TAB 2: GESTURES ---
        f_ge = ctk.CTkScrollableFrame(tab_gestures, fg_color="transparent")
        f_ge.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(f_ge, text="Biometric Gesture Mapping & Thresholds", font=("Helvetica", 13, "bold"), text_color="#1E293B").pack(anchor="w", pady=(4, 8))

        def _add_gesture_card(parent, icon, name, trigger, action):
            c = ctk.CTkFrame(parent, fg_color="#F8FAFC", corner_radius=8, border_width=1, border_color="#E2E8F0")
            c.pack(fill="x", pady=4)
            row = ctk.CTkFrame(c, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=8)
            ctk.CTkLabel(row, text=icon, font=("Segoe UI Emoji", 20)).pack(side="left", padx=(0, 12))
            col = ctk.CTkFrame(row, fg_color="transparent")
            col.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(col, text=name, font=("Helvetica", 12, "bold"), text_color="#1E293B").pack(anchor="w")
            ctk.CTkLabel(col, text=f"Trigger: {trigger}", font=("Helvetica", 10, "italic"), text_color="#2563EB").pack(anchor="w")
            ctk.CTkLabel(col, text=f"Action: {action}", font=("Helvetica", 10), text_color="#475569").pack(anchor="w")

        _add_gesture_card(f_ge, "👃", "Nose Glide", "Nose Tip Landmark #1 offset from calibrated center", "Moves mouse cursor smoothly across monitors")
        _add_gesture_card(f_ge, "😉", "Left Wink", "Left EAR drops below threshold (Right Eye open)", "Left Click (selects items, triggers buttons)")
        _add_gesture_card(f_ge, "😉", "Right Wink", "Right EAR drops below threshold (Left Eye open)", "Right Click (opens context menus)")
        _add_gesture_card(f_ge, "😁", "Wide Smile", "Lip corners stretched horizontally beyond baseline", "Drag & Drop (holds left button while smile is sustained)")
        _add_gesture_card(f_ge, "😴", "Long Blink", "Both eyes closed for > 0.6 seconds", "Toggles Scroll Mode (head pitch scrolls pages up/down)")
        _add_gesture_card(f_ge, "👄", "Mouth Open", "Mouth Aspect Ratio (MAR) > 0.32 for > 0.6 seconds", "Safety Switch: Pauses/Resumes mouse cursor tracking")

        # --- TAB 3: ARCHITECTURE ---
        f_ar = ctk.CTkScrollableFrame(tab_arch, fg_color="transparent")
        f_ar.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(f_ar, text="Software Architecture: Model-View-Controller (MVC)", font=("Helvetica", 13, "bold"), text_color="#1E293B").pack(anchor="w", pady=(4, 6))
        arch_desc = (
            "The system is structured into a clean decoupled MVC pattern:\n"
            "• Model: MediaPipe 3D Face Landmarker (468 points) and biometric calculation pipelines (EAR, MAR, 1-Euro smoothing filters).\n"
            "• View: CustomTkinter reactive UI (`ui.py`) with 30 FPS video feed rendering and state monitoring badges.\n"
            "• Controller: Core thread (`run.py`) and discrete action engines (`actions/cursor_controller.py`, `click_controller.py`, `scroll_controller.py`, `drag_controller.py`).\n"
            "• Persistence: SQLite Database (`utils/database.py`) storing camera IP addresses, timestamps, and connection status."
        )
        ctk.CTkLabel(f_ar, text=arch_desc, font=("Helvetica", 11), text_color="#475569", justify="left", wraplength=580).pack(anchor="w", pady=(0, 12))

        ctk.CTkLabel(f_ar, text="Technology Stack", font=("Helvetica", 13, "bold"), text_color="#1E293B").pack(anchor="w", pady=(6, 6))

        def _add_tech(parent, name, role):
            r = ctk.CTkFrame(parent, fg_color="#F1F5F9", corner_radius=6)
            r.pack(fill="x", pady=3)
            ctk.CTkLabel(r, text=name, font=("Helvetica", 11, "bold"), text_color="#0F172A", width=140, anchor="w").pack(side="left", padx=12, pady=6)
            ctk.CTkLabel(r, text=role, font=("Helvetica", 10), text_color="#475569", anchor="w").pack(side="left", fill="x", expand=True, padx=6)

        _add_tech(f_ar, "Python 3.10+", "Primary runtime environment and system integration")
        _add_tech(f_ar, "Google MediaPipe", "On-device 3D facial landmark perception (Tasks Vision API)")
        _add_tech(f_ar, "OpenCV (cv2)", "Real-time webcam video capture & DroidCam streaming")
        _add_tech(f_ar, "CustomTkinter", "Modern high-DPI accessible user interface")
        _add_tech(f_ar, "PyAutoGUI & ctypes", "Low-latency OS cursor movement and click simulation")
        _add_tech(f_ar, "SQLite3 (connections.db)", "Local relational database storing DroidCam IPs & connection logs")

        # --- TAB 4: ACADEMIC DETAILS ---
        f_ac = ctk.CTkFrame(tab_academic, fg_color="transparent")
        f_ac.pack(fill="both", expand=True, padx=20, pady=16)

        ctk.CTkLabel(f_ac, text="Project & Institutional Credentials", font=("Helvetica", 14, "bold"), text_color="#1E293B").pack(anchor="w", pady=(0, 12))

        card_ac = ctk.CTkFrame(f_ac, fg_color="#F8FAFC", corner_radius=10, border_width=1, border_color="#E2E8F0")
        card_ac.pack(fill="x", pady=6)

        rows_info = [
            ("Project Title:", "EyePilot: A Computer Vision-Based Virtual Mouse System"),
            ("Developer:", "Aruna Bharathi S. Angalaeswari S. Brainee Christina S."),
            ("Department:", "Department of Computer Science & Engineering"),
            ("Institution:", "P. A. College of Engineering and Technology"),
            ("Academic Year:", "2025 – 2026"),
            
        ]

        for k, v in rows_info:
            r = ctk.CTkFrame(card_ac, fg_color="transparent")
            r.pack(fill="x", padx=16, pady=6)
            ctk.CTkLabel(r, text=k, font=("Helvetica", 11, "bold"), text_color="#334155", width=140, anchor="w").pack(side="left")
            ctk.CTkLabel(r, text=v, font=("Helvetica", 11), text_color="#0F172A", anchor="w").pack(side="left", fill="x", expand=True)

        # Bottom Close button
        ctk.CTkButton(
            self.about_window, text="Close", fg_color="#182A4A", hover_color="#243C66",
            font=("Helvetica", 12, "bold"), height=36, corner_radius=8,
            command=self.about_window.destroy
        ).pack(fill="x", padx=18, pady=(0, 14))

    # --- UI UPDATE HELPERS ---
    def _add_badge(self, parent, key, icon, title, initial_val, color_type):
        row = ctk.CTkFrame(parent, fg_color="transparent", height=30)
        row.pack(fill="x", padx=18, pady=2)
        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left, text=icon, font=("Segoe UI Emoji", 13)).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(left, text=title, font=("Helvetica", 12), text_color="#334155").pack(side="left")

        colors = {"green": ("#DCFCE7", "#15803D"), "red": ("#FEE2E2", "#B91C1C"),
                  "blue": ("#E0F2FE", "#0369A1"), "neutral": ("#F1F5F9", "#64748B")}
        bg, fg = colors.get(color_type, colors["neutral"])
        badge = ctk.CTkLabel(row, text=initial_val, fg_color=bg, text_color=fg, corner_radius=8,
                             font=("Helvetica", 10, "bold"), width=130, height=22)
        badge.pack(side="right")
        self.badges[key] = badge

    def update_badge(self, key, text, color_type):
        colors = {"green": ("#DCFCE7", "#15803D"), "red": ("#FEE2E2", "#B91C1C"),
                  "blue": ("#E0F2FE", "#0369A1"), "neutral": ("#F1F5F9", "#64748B")}
        bg, fg = colors.get(color_type, colors["neutral"])
        if key in self.badges:
            self.badges[key].configure(text=text, fg_color=bg, text_color=fg)

    def _build_card(self, parent, icon, title, desc, bg):
        tile = ctk.CTkFrame(parent, fg_color=bg, corner_radius=10)
        tile.pack(side="left", fill="both", expand=True, padx=4)
        ctk.CTkLabel(tile, text=icon, font=("Segoe UI Emoji", 20)).pack(pady=(10, 2))
        ctk.CTkLabel(tile, text=title, font=("Helvetica", 11, "bold"), text_color="#1E293B").pack(pady=(0, 1))
        ctk.CTkLabel(tile, text=desc, font=("Helvetica", 9), text_color="#64748B").pack(pady=(0, 6))

    def get_cam_choice(self):
        return self.cam_selector.get()

    def get_ip_input(self):
        if hasattr(self, 'ip_combo'):
            return self.ip_combo.get().strip()
        return self.ip_entry.get().strip()

    def set_ip_input(self, ip):
        if hasattr(self, 'ip_combo'):
            self.ip_combo.set(ip)
        elif hasattr(self, 'ip_entry') and hasattr(self.ip_entry, 'delete'):
            self.ip_entry.delete(0, 'end')
            self.ip_entry.insert(0, ip)

    def refresh_ip_list(self):
        if hasattr(self, 'ip_combo'):
            recent = db.get_recent_ips()
            if not recent and self.saved_ip:
                recent = [self.saved_ip]
            if recent:
                self.ip_combo.configure(values=recent)

    def get_mirror_state(self):
        return self.mirror_var.get()

    def set_mirror_state(self, state):
        self.mirror_var.set(state)

    def update_camera_indicator(self, text, is_active):
        if is_active:
            self.lbl_camera_badge.configure(text=text, fg_color="#10B981", text_color="#FFFFFF")
        else:
            self.lbl_camera_badge.configure(text=text, fg_color="#374151", text_color="#9CA3AF")

    def get_video_dimensions(self):
        return self.video_container.winfo_width(), self.video_container.winfo_height()

    def set_video_frame(self, ctk_image):
        self.video_display.configure(image=ctk_image)

    def clear_video_frame(self):
        self.video_display.configure(image="")