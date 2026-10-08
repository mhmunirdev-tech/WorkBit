"use client";

import { useEffect, useState } from "react";
import { ImagePlus, Pencil, Plus, Trash2, Upload } from "lucide-react";
import { api } from "../lib/api";
import { Alert, AlertDescription } from "./ui/alert";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";

type Banner = {
  id: string;
  title: string;
  content: string;
  image_url: string;
  link_url: string | null;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

type BannerForm = {
  title: string;
  content: string;
  image_url: string;
  link_url: string;
  is_active: boolean;
  sort_order: string;
};

const emptyForm: BannerForm = {
  title: "",
  content: "",
  image_url: "",
  link_url: "",
  is_active: false,
  sort_order: "0",
};

export function AdminBanners() {
  const [banners, setBanners] = useState<Banner[]>([]);
  const [form, setForm] = useState<BannerForm>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function loadBanners() {
    setLoading(true);
    setError("");
    try {
      setBanners(await api<Banner[]>("/admin/dashboard-banners"));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Banners could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadBanners();
  }, []);

  function editBanner(banner: Banner) {
    setEditingId(banner.id);
    setForm({
      title: banner.title,
      content: banner.content,
      image_url: banner.image_url,
      link_url: banner.link_url ?? "",
      is_active: banner.is_active,
      sort_order: String(banner.sort_order),
    });
    setNotice("");
    setError("");
  }

  function resetForm() {
    setEditingId(null);
    setForm(emptyForm);
  }

  async function uploadImage(file: File | undefined) {
    if (!file) return;
    setError("");
    setNotice("");
    setUploading(true);
    try {
      const payload = new FormData();
      payload.set("file", file);
      const result = await api<{ image_url: string }>("/admin/dashboard-banners/upload-image", {
        method: "POST",
        body: payload,
      });
      setForm((previous) => ({ ...previous, image_url: result.image_url }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Banner image upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function saveBanner(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    const payload = {
      ...form,
      link_url: form.link_url.trim() || null,
      sort_order: Number(form.sort_order),
    };
    try {
      const path = editingId
        ? `/admin/dashboard-banners/${editingId}`
        : "/admin/dashboard-banners";
      await api<Banner>(path, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      await loadBanners();
      setNotice(editingId ? "Banner updated." : "Banner created.");
      resetForm();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Banner could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function deleteBanner(banner: Banner) {
    if (!window.confirm(`Delete the "${banner.title}" banner? This cannot be undone.`)) return;
    setError("");
    setNotice("");
    try {
      await api<void>(`/admin/dashboard-banners/${banner.id}/delete`, { method: "POST" });
      setBanners((current) => current.filter((item) => item.id !== banner.id));
      if (editingId === banner.id) resetForm();
      setNotice("Banner deleted.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Banner could not be deleted.");
    }
  }

  return (
    <main className="admin-banners-page">
      <header className="admin-dashboard-header">
        <div>
          <p className="eyebrow">DASHBOARD CONTENT</p>
          <h1>Banner CMS</h1>
          <p>Create and publish image announcements shown below the user dashboard header.</p>
        </div>
        <Button variant="outline" type="button" onClick={() => { resetForm(); setError(""); setNotice(""); }}>
          <Plus size={16} /> New banner
        </Button>
      </header>

      {error && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}
      {notice && <Alert className="admin-banner-notice" role="status"><AlertDescription>{notice}</AlertDescription></Alert>}

      <div className="admin-banners-layout">
        <Card className="admin-banner-form-card" asChild>
          <form onSubmit={(event) => void saveBanner(event)}>
            <div className="admin-section-heading">
              <div>
                <p className="eyebrow">{editingId ? "EDIT CONTENT" : "NEW CONTENT"}</p>
                <h2>{editingId ? "Update banner" : "Create a banner"}</h2>
              </div>
              <span className="admin-shortcut-icon"><ImagePlus size={18} /></span>
            </div>

            <label className="admin-banner-field">
              <span>Title</span>
              <Input required maxLength={120} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="A short announcement title" />
            </label>
            <label className="admin-banner-field">
              <span>Content</span>
              <textarea className="admin-banner-textarea" maxLength={500} rows={4} value={form.content} onChange={(event) => setForm({ ...form, content: event.target.value })} placeholder="Add a few helpful details for users." />
              <small>{form.content.length}/500 characters</small>
            </label>
            <div className="admin-banner-field">
              <span>Banner image <small>(JPEG, PNG or WebP; max 5 MB)</small></span>
              <label className="admin-banner-upload">
                <Upload size={16} />
                {uploading ? "Uploading image…" : form.image_url ? "Replace image" : "Choose image"}
                <input type="file" accept="image/jpeg,image/png,image/webp" disabled={uploading} onChange={(event) => { void uploadImage(event.target.files?.[0]); event.currentTarget.value = ""; }} />
              </label>
              {form.image_url ? (
                <div className="admin-banner-image-preview">
                  <img src={form.image_url} alt="Selected banner preview" />
                </div>
              ) : (
                <p className="admin-banner-hint">Upload an image before publishing this banner.</p>
              )}
            </div>
            <label className="admin-banner-field">
              <span>Optional destination URL</span>
              <Input type="text" maxLength={1024} value={form.link_url} onChange={(event) => setForm({ ...form, link_url: event.target.value })} placeholder="/offers or https://example.com" />
              <small>You can also enter a site path beginning with “/”.</small>
            </label>
            <label className="admin-banner-field">
              <span>Display order</span>
              <Input type="number" min={0} max={10000} step={1} value={form.sort_order} onChange={(event) => setForm({ ...form, sort_order: event.target.value })} />
              <small>Lower numbers appear first.</small>
            </label>
            <label className="admin-banner-checkbox">
              <input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} />
              <span><strong>Publish on dashboard</strong><small>Only published banners are visible to signed-in users.</small></span>
            </label>
            <div className="admin-banner-form-actions">
              <Button type="submit" disabled={saving || uploading || !form.image_url}>
                {saving ? "Saving…" : editingId ? "Save changes" : "Create banner"}
              </Button>
              {editingId && <Button variant="outline" type="button" onClick={resetForm}>Cancel edit</Button>}
            </div>
          </form>
        </Card>

        <section className="admin-banner-list" aria-labelledby="admin-banner-list-heading">
          <div className="admin-section-heading">
            <div><p className="eyebrow">CONTENT LIBRARY</p><h2 id="admin-banner-list-heading">Dashboard banners</h2></div>
            <span className="admin-banner-count">{banners.length}</span>
          </div>
          {loading ? (
            <p className="admin-banner-empty">Loading banners…</p>
          ) : banners.length === 0 ? (
            <Card className="admin-banner-empty"><ImagePlus size={25} /><strong>No banners yet</strong><span>Create your first dashboard announcement.</span></Card>
          ) : (
            <div className="admin-banner-items">
              {banners.map((banner) => (
                <Card className="admin-banner-item" key={banner.id}>
                  <img src={banner.image_url} alt="" />
                  <div className="admin-banner-item-copy">
                    <div className="admin-banner-item-title">
                      <strong>{banner.title}</strong>
                      <span className={banner.is_active ? "is-published" : "is-draft"}>{banner.is_active ? "Published" : "Draft"}</span>
                    </div>
                    <p>{banner.content || "No description"}</p>
                    <small>Order {banner.sort_order}{banner.link_url ? ` · ${banner.link_url}` : ""}</small>
                    <div className="admin-banner-item-actions">
                      <Button variant="outline" size="sm" type="button" onClick={() => editBanner(banner)}><Pencil size={14} /> Edit</Button>
                      <Button variant="outline" size="sm" type="button" onClick={() => void deleteBanner(banner)}><Trash2 size={14} /> Delete</Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
