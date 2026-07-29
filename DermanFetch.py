import customtkinter as ctk
import yt_dlp
import threading
from tkinter import filedialog
import os
import imageio_ffmpeg  # Otomatik FFmpeg yönetimi sağlayan kütüphane

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class DermanFetchApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("DermanFetch v1.0")
        self.geometry("620x650")
        self.resizable(False, False)

        # İkon Kontrolü (Aynı klasörde icon.ico varsa pencereye ekler)
        if os.path.exists("icon.ico"):
            self.iconbitmap("icon.ico")

        # Varsayılan indirme konumu (İndirilenler Klasörü)
        self.download_folder = os.path.join(os.path.expanduser("~"), "Downloads")
        self.download_queue = []
        self.history = []
        self.is_downloading = False

        # Başlık
        self.title_label = ctk.CTkLabel(self, text="DermanFetch v1.0", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(pady=(15, 5))

        # Sekmeler
        self.tabview = ctk.CTkTabview(self, width=580, height=480)
        self.tabview.pack(pady=10, padx=10)

        self.tab_single = self.tabview.add("Tekli İndirme")
        self.tab_batch = self.tabview.add("Toplu İndirme")
        self.tab_history = self.tabview.add("İndirilenler")
        self.tab_settings = self.tabview.add("Ayarlar")

        # Sekme İçerikleri
        self.setup_single_tab()
        self.setup_batch_tab()
        self.setup_history_tab()
        self.setup_settings_tab()

        # Alt Bilgi
        self.platforms_label = ctk.CTkLabel(
            self, 
            text="Desteklenenler: YouTube, Instagram, TikTok, X, Reddit, Twitch, SoundCloud vb.", 
            font=ctk.CTkFont(size=10), 
            text_color="gray50"
        )
        self.platforms_label.pack(side="bottom", pady=10)

    # ---------------- TEKLİ İNDİRME ----------------
    def setup_single_tab(self):
        frame = self.tab_single

        ctk.CTkLabel(frame, text="Tekli Medya İndirici", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=15)

        self.single_url_entry = ctk.CTkEntry(frame, placeholder_text="Video / Müzik Linkini Buraya Yapıştırın...", width=450, height=38)
        self.single_url_entry.pack(pady=10)

        self.single_format_var = ctk.StringVar(value="mp4")
        rf = ctk.CTkFrame(frame, fg_color="transparent")
        rf.pack(pady=10)
        ctk.CTkRadioButton(rf, text="Video (MP4)", variable=self.single_format_var, value="mp4").pack(side="left", padx=15)
        ctk.CTkRadioButton(rf, text="Sadece Ses (MP3)", variable=self.single_format_var, value="mp3").pack(side="left", padx=15)

        self.single_progress = ctk.CTkProgressBar(frame, width=450)
        self.single_progress.pack(pady=(20, 5))
        self.single_progress.set(0)

        self.single_progress_label = ctk.CTkLabel(frame, text="%0", font=ctk.CTkFont(size=11))
        self.single_progress_label.pack(pady=2)

        self.single_download_btn = ctk.CTkButton(frame, text="Hemen İndir", command=self.download_single, height=40, width=220, font=ctk.CTkFont(weight="bold"))
        self.single_download_btn.pack(pady=15)

        self.single_status = ctk.CTkLabel(frame, text="", font=ctk.CTkFont(size=12))
        self.single_status.pack(pady=5)

    def download_single(self):
        url = self.single_url_entry.get().strip()
        if not url:
            self.single_status.configure(text="Lütfen bir link girin!", text_color="red")
            return

        threading.Thread(target=self._process_single_download, args=(url,), daemon=True).start()

    def _process_single_download(self, url):
        self.single_status.configure(text="İndiriliyor...", text_color="yellow")
        self.single_download_btn.configure(state="disabled")

        fmt = self.single_format_var.get()
        out_path = os.path.join(self.download_folder, '%(title)s.%(ext)s')
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

        def hook(d):
            if d['status'] == 'downloading':
                tot = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                dw = d.get('downloaded_bytes', 0)
                if tot > 0:
                    p = dw / tot
                    self.single_progress.set(p)
                    self.single_progress_label.configure(text=f"%{int(p*100)}")

        # MP3 ve MP4 İndirme Ayarları (imageio-ffmpeg Destekli)
        if fmt == 'mp3':
            ydl_opts = {
                'outtmpl': out_path,
                'progress_hooks': [hook],
                'format': 'bestaudio/best',
                'ffmpeg_location': ffmpeg_exe,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
        else:
            ydl_opts = {
                'outtmpl': out_path,
                'progress_hooks': [hook],
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'ffmpeg_location': ffmpeg_exe,
            }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                if fmt == 'mp3':
                    filename = os.path.splitext(filename)[0] + ".mp3"
                self.add_to_history(info.get('title', 'Bilinmeyen Medya'), url, filename)

            self.single_status.configure(text="İndirme Tamamlandı! 🎉", text_color="green")
            self.single_url_entry.delete(0, 'end')
        except Exception as e:
            self.single_status.configure(text="İndirme Hatası!", text_color="red")
            print(f"Hata detayı: {e}")
        finally:
            self.single_download_btn.configure(state="normal")

    # ---------------- TOPLU İNDİRME ----------------
    def setup_batch_tab(self):
        frame = self.tab_batch

        entry_frame = ctk.CTkFrame(frame, fg_color="transparent")
        entry_frame.pack(pady=10)

        self.batch_url_entry = ctk.CTkEntry(entry_frame, placeholder_text="Link Yapıştırın...", width=340, height=35)
        self.batch_url_entry.pack(side="left", padx=(0, 10))

        ctk.CTkButton(entry_frame, text="Sıraya Ekle", command=self.add_to_batch, width=100, height=35).pack(side="left")

        self.batch_box = ctk.CTkTextbox(frame, width=460, height=140)
        self.batch_box.pack(pady=5)
        self.update_batch_box()

        self.batch_format_var = ctk.StringVar(value="mp4")
        rf = ctk.CTkFrame(frame, fg_color="transparent")
        rf.pack(pady=5)
        ctk.CTkRadioButton(rf, text="Video (MP4)", variable=self.batch_format_var, value="mp4").pack(side="left", padx=15)
        ctk.CTkRadioButton(rf, text="Sadece Ses (MP3)", variable=self.batch_format_var, value="mp3").pack(side="left", padx=15)

        self.batch_progress = ctk.CTkProgressBar(frame, width=460)
        self.batch_progress.pack(pady=(10, 2))
        self.batch_progress.set(0)

        self.batch_progress_label = ctk.CTkLabel(frame, text="%0", font=ctk.CTkFont(size=11))
        self.batch_progress_label.pack(pady=2)

        bf = ctk.CTkFrame(frame, fg_color="transparent")
        bf.pack(pady=5)
        self.batch_start_btn = ctk.CTkButton(bf, text="Toplu İndirmeyi Başlat", command=self.start_batch_download, height=36, width=200, font=ctk.CTkFont(weight="bold"))
        self.batch_start_btn.pack(side="left", padx=5)

        ctk.CTkButton(bf, text="Sırayı Temizle", command=self.clear_batch, height=36, width=110, fg_color="gray30").pack(side="left", padx=5)

        self.batch_status = ctk.CTkLabel(frame, text="", font=ctk.CTkFont(size=12))
        self.batch_status.pack(pady=5)

    def add_to_batch(self):
        url = self.batch_url_entry.get().strip()
        if url:
            self.download_queue.append(url)
            self.batch_url_entry.delete(0, 'end')
            self.update_batch_box()

    def clear_batch(self):
        if not self.is_downloading:
            self.download_queue.clear()
            self.update_batch_box()

    def update_batch_box(self):
        self.batch_box.configure(state="normal")
        self.batch_box.delete("1.0", "end")
        if not self.download_queue:
            self.batch_box.insert("1.0", "--- Toplu İndirme Sırası (Boş) ---\n")
        else:
            for idx, item in enumerate(self.download_queue, start=1):
                self.batch_box.insert("end", f"{idx}. {item}\n")
        self.batch_box.configure(state="disabled")

    def start_batch_download(self):
        if self.download_queue and not self.is_downloading:
            threading.Thread(target=self._process_batch_download, daemon=True).start()

    def _process_batch_download(self):
        self.is_downloading = True
        self.batch_start_btn.configure(state="disabled")

        tot_items = len(self.download_queue)
        fmt = self.batch_format_var.get()
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

        while self.download_queue:
            url = self.download_queue[0]
            curr_idx = tot_items - len(self.download_queue) + 1
            self.batch_status.configure(text=f"İndiriliyor [{curr_idx}/{tot_items}]...", text_color="yellow")

            def hook(d):
                if d['status'] == 'downloading':
                    tot = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    dw = d.get('downloaded_bytes', 0)
                    if tot > 0:
                        p = dw / tot
                        self.batch_progress.set(p)
                        self.batch_progress_label.configure(text=f"%{int(p*100)}")

            out_path = os.path.join(self.download_folder, '%(title)s.%(ext)s')
            
            if fmt == 'mp3':
                ydl_opts = {
                    'outtmpl': out_path,
                    'progress_hooks': [hook],
                    'format': 'bestaudio/best',
                    'ffmpeg_location': ffmpeg_exe,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                }
            else:
                ydl_opts = {
                    'outtmpl': out_path,
                    'progress_hooks': [hook],
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'ffmpeg_location': ffmpeg_exe,
                }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    if fmt == 'mp3':
                        filename = os.path.splitext(filename)[0] + ".mp3"
                    self.add_to_history(info.get('title', 'Bilinmeyen Medya'), url, filename)
                
                self.download_queue.pop(0)
                self.update_batch_box()
            except Exception as e:
                print(f"Hata: {e}")
                self.download_queue.pop(0)
                self.update_batch_box()

        self.batch_status.configure(text="Toplu İndirme Tamamlandı! 🎉", text_color="green")
        self.is_downloading = False
        self.batch_start_btn.configure(state="normal")

    # ---------------- İNDİRİLENLER (GEÇMİŞ) ----------------
    def setup_history_tab(self):
        frame = self.tab_history

        ctk.CTkLabel(frame, text="İndirme Geçmişi", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        self.history_box = ctk.CTkTextbox(frame, width=480, height=280)
        self.history_box.pack(pady=5)
        self.update_history_box()

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="Seçilen Linki Tekrar İndir", command=self.re_download_selected, width=180).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Geçmişi Temizle", command=self.clear_history, width=130, fg_color="gray30").pack(side="left", padx=5)

    def add_to_history(self, title, url, file_path):
        item = {"title": title, "url": url, "path": file_path}
        self.history.append(item)
        self.update_history_box()

    def update_history_box(self):
        self.history_box.configure(state="normal")
        self.history_box.delete("1.0", "end")
        if not self.history:
            self.history_box.insert("1.0", "Henüz indirilen bir medya yok.\n")
        else:
            for idx, item in enumerate(reversed(self.history), start=1):
                self.history_box.insert("end", f"{idx}. {item['title']}\n   Link: {item['url']}\n   Konum: {item['path']}\n\n")
        self.history_box.configure(state="disabled")

    def clear_history(self):
        self.history.clear()
        self.update_history_box()

    def re_download_selected(self):
        if self.history:
            last_url = self.history[-1]["url"]
            self.single_url_entry.delete(0, 'end')
            self.single_url_entry.insert(0, last_url)
            self.tabview.set("Tekli İndirme")

    # ---------------- AYARLAR ----------------
    def setup_settings_tab(self):
        frame = self.tab_settings

        ctk.CTkLabel(frame, text="Uygulama Ayarları", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=15)

        folder_frame = ctk.CTkFrame(frame)
        folder_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(folder_frame, text="Varsayılan İndirme Klasörü:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=5)
        
        self.settings_folder_label = ctk.CTkLabel(folder_frame, text=self.download_folder, text_color="gray")
        self.settings_folder_label.pack(side="left", padx=10, pady=5)
        ctk.CTkButton(folder_frame, text="Değiştir", command=self.change_folder_setting, width=80).pack(side="right", padx=10, pady=5)

        theme_frame = ctk.CTkFrame(frame)
        theme_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(theme_frame, text="Arayüz Teması:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=5)
        
        self.theme_var = ctk.StringVar(value="Koyu (Dark)")
        ctk.CTkOptionMenu(theme_frame, variable=self.theme_var, values=["Koyu (Dark)", "Açık (Light)"], command=self.change_theme).pack(padx=10, pady=5, anchor="w")

    def change_folder_setting(self):
        folder = filedialog.askdirectory()
        if folder:
            self.download_folder = folder
            self.settings_folder_label.configure(text=folder)

    def change_theme(self, choice):
        if choice == "Koyu (Dark)":
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")

if __name__ == "__main__":
    app = DermanFetchApp()
    app.mainloop()