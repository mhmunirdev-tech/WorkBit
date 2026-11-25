"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { PackageOpen, Plus, RefreshCw, Save, ShoppingBag } from "lucide-react";
import { api } from "../lib/api";
import { showToast } from "../lib/toast";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";

type Category = { id: string; name: string; slug: string; description: string; is_active: boolean; sort_order: number; product_count: number };
type Product = { id: string; category_id: string; category_name: string; sku: string; name: string; slug: string; description: string; image_url: string | null; price: string; currency: string; stock_quantity: number; is_active: boolean; featured: boolean; sort_order: number };
type Order = { id: string; status: string; total: string; currency: string; user_name: string | null; user_email: string | null; shipping_name: string; shipping_phone: string; shipping_address: string; shipping_city: string; created_at: string; items: { product_name: string; quantity: number }[] };
type ProductForm = { category_id: string; sku: string; name: string; slug: string; description: string; image_url: string; price: string; stock_quantity: string; is_active: boolean; featured: boolean; sort_order: string };

const emptyProduct: ProductForm = { category_id: "", sku: "", name: "", slug: "", description: "", image_url: "", price: "", stock_quantity: "0", is_active: false, featured: false, sort_order: "0" };
const statuses = ["PENDING", "CONFIRMED", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"];

function money(value: string, currency: string) {
  return new Intl.NumberFormat("en-BD", { style: "currency", currency, minimumFractionDigits: 2 }).format(Number(value));
}

export function AdminMarketplace() {
  const [tab, setTab] = useState<"products" | "categories" | "orders">("products");
  const [categories, setCategories] = useState<Category[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [categoryForm, setCategoryForm] = useState({ name: "", slug: "", description: "", sort_order: "0" });
  const [productForm, setProductForm] = useState<ProductForm>(emptyProduct);
  const [editingId, setEditingId] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [categoryData, productData, orderData] = await Promise.all([
        api<Category[]>("/admin/marketplace/categories"),
        api<Product[]>("/admin/marketplace/products"),
        api<Order[]>("/admin/marketplace/orders"),
      ]);
      setCategories(categoryData);
      setProducts(productData);
      setOrders(orderData);
      setProductForm((current) => current.category_id || !categoryData[0] ? current : { ...current, category_id: categoryData[0].id });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Marketplace management data could not be loaded.");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function createCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("category");
    setError("");
    try {
      const category = await api<Category>("/admin/marketplace/categories", { method: "POST", body: JSON.stringify({ ...categoryForm, sort_order: Number(categoryForm.sort_order) }) });
      setCategories((items) => [...items, category]);
      setCategoryForm({ name: "", slug: "", description: "", sort_order: "0" });
      showToast({ title: "Category created", description: `${category.name} is ready for products.`, variant: "success" });
    } catch (reason) { setError(reason instanceof Error ? reason.message : "The category could not be created."); }
    finally { setBusy(""); }
  }

  async function saveProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("product");
    setError("");
    try {
      const payload = { ...productForm, image_url: productForm.image_url || null, price: productForm.price, stock_quantity: Number(productForm.stock_quantity), sort_order: Number(productForm.sort_order), currency: "BDT" };
      const path = editingId ? `/admin/marketplace/products/${editingId}` : "/admin/marketplace/products";
      const product = await api<Product>(path, { method: editingId ? "PUT" : "POST", body: JSON.stringify(payload) });
      setProducts((items) => editingId ? items.map((item) => item.id === product.id ? product : item) : [product, ...items]);
      setProductForm({ ...emptyProduct, category_id: categories[0]?.id || "" });
      setEditingId("");
      showToast({ title: editingId ? "Product updated" : "Product created", description: `${product.name} is saved.`, variant: "success" });
    } catch (reason) { setError(reason instanceof Error ? reason.message : "The product could not be saved."); }
    finally { setBusy(""); }
  }

  async function updateOrder(order: Order, status: string) {
    setBusy(order.id);
    setError("");
    try {
      const updated = await api<Order>(`/admin/marketplace/orders/${order.id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      setOrders((items) => items.map((item) => item.id === updated.id ? updated : item));
      showToast({ title: "Order updated", description: `Order #${order.id.slice(0, 8)} is now ${status.toLowerCase()}.`, variant: "success" });
    } catch (reason) { setError(reason instanceof Error ? reason.message : "The order could not be updated."); }
    finally { setBusy(""); }
  }

  function editProduct(product: Product) {
    setTab("products");
    setEditingId(product.id);
    setProductForm({ category_id: product.category_id, sku: product.sku, name: product.name, slug: product.slug, description: product.description, image_url: product.image_url || "", price: product.price, stock_quantity: String(product.stock_quantity), is_active: product.is_active, featured: product.featured, sort_order: String(product.sort_order) });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <main className="admin-marketplace-page">
      <header className="admin-withdrawals-header"><div><p className="eyebrow">WORKBIT / MARKETPLACE</p><h1>Products & orders</h1><p>Manage the first-party product catalog separately from earning packages and wallet balances.</p></div><Button className="secondary-button" variant="outline" type="button" onClick={() => void load()} disabled={loading}><RefreshCw size={15} /> Refresh</Button></header>
      {error && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}
      <div className="admin-marketplace-tabs" role="tablist" aria-label="Marketplace sections"><Button type="button" variant={tab === "products" ? "default" : "outline"} onClick={() => setTab("products")}><ShoppingBag size={15} /> Products ({products.length})</Button><Button type="button" variant={tab === "categories" ? "default" : "outline"} onClick={() => setTab("categories")}><Plus size={15} /> Categories ({categories.length})</Button><Button type="button" variant={tab === "orders" ? "default" : "outline"} onClick={() => setTab("orders")}><PackageOpen size={15} /> Orders ({orders.length})</Button></div>
      {loading ? <Card className="panel marketplace-empty">Loading marketplace management…</Card> : <>
        {tab === "categories" && <section className="admin-marketplace-layout"><Card className="panel admin-marketplace-form-card"><p className="eyebrow">NEW CATEGORY</p><h2>Create category</h2><form className="admin-marketplace-form" onSubmit={(event) => void createCategory(event)}><label>Name<Input required value={categoryForm.name} onChange={(event) => setCategoryForm({ ...categoryForm, name: event.target.value })} /></label><label>Slug<Input required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" placeholder="electronics-accessories" value={categoryForm.slug} onChange={(event) => setCategoryForm({ ...categoryForm, slug: event.target.value })} /></label><label>Description<Textarea rows={3} value={categoryForm.description} onChange={(event) => setCategoryForm({ ...categoryForm, description: event.target.value })} /></label><label>Display order<Input type="number" min="0" value={categoryForm.sort_order} onChange={(event) => setCategoryForm({ ...categoryForm, sort_order: event.target.value })} /></label><Button className="primary" type="submit" disabled={busy === "category"}>{busy === "category" ? "Creating…" : "Create category"}</Button></form></Card><Card className="panel admin-marketplace-list-card"><p className="eyebrow">CATALOG STRUCTURE</p><h2>Categories</h2><div className="admin-marketplace-category-list">{categories.map((category) => <div className="admin-marketplace-category-row" key={category.id}><div><strong>{category.name}</strong><small>/{category.slug}</small></div><Badge variant="outline">{category.product_count} products</Badge></div>)}</div></Card></section>}

        {tab === "products" && <section className="admin-marketplace-layout"><Card className="panel admin-marketplace-form-card"><p className="eyebrow">{editingId ? "EDIT PRODUCT" : "NEW PRODUCT"}</p><h2>{editingId ? "Update product" : "Add a product"}</h2><form className="admin-marketplace-form" onSubmit={(event) => void saveProduct(event)}><label>Category<select value={productForm.category_id} onChange={(event) => setProductForm({ ...productForm, category_id: event.target.value })} required><option value="">Choose category</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label><div className="admin-marketplace-form-grid"><label>Product name<Input required value={productForm.name} onChange={(event) => setProductForm({ ...productForm, name: event.target.value })} /></label><label>SKU<Input required value={productForm.sku} onChange={(event) => setProductForm({ ...productForm, sku: event.target.value })} /></label></div><label>Slug<Input required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" placeholder="desk-lamp" value={productForm.slug} onChange={(event) => setProductForm({ ...productForm, slug: event.target.value })} /></label><label>Description<Textarea rows={4} value={productForm.description} onChange={(event) => setProductForm({ ...productForm, description: event.target.value })} /></label><label>Image URL (optional)<Input type="url" value={productForm.image_url} onChange={(event) => setProductForm({ ...productForm, image_url: event.target.value })} /></label><div className="admin-marketplace-form-grid"><label>Price (BDT)<Input required type="number" min="0.01" step="0.01" value={productForm.price} onChange={(event) => setProductForm({ ...productForm, price: event.target.value })} /></label><label>Stock quantity<Input required type="number" min="0" step="1" value={productForm.stock_quantity} onChange={(event) => setProductForm({ ...productForm, stock_quantity: event.target.value })} /></label></div><div className="admin-marketplace-checkboxes"><label><input type="checkbox" checked={productForm.is_active} onChange={(event) => setProductForm({ ...productForm, is_active: event.target.checked })} /> Publish product</label><label><input type="checkbox" checked={productForm.featured} onChange={(event) => setProductForm({ ...productForm, featured: event.target.checked })} /> Featured</label></div><div className="admin-marketplace-form-actions"><Button className="primary" type="submit" disabled={busy === "product" || !categories.length}>{busy === "product" ? "Saving…" : <><Save size={15} /> {editingId ? "Save changes" : "Create product"}</>}</Button>{editingId && <Button variant="outline" type="button" onClick={() => { setEditingId(""); setProductForm({ ...emptyProduct, category_id: categories[0]?.id || "" }); }}>Cancel</Button>}</div></form></Card><Card className="panel admin-marketplace-list-card"><p className="eyebrow">PRODUCT CATALOG</p><h2>Products</h2>{products.length === 0 ? <div className="marketplace-empty"><ShoppingBag size={24} /><p>No products created yet.</p></div> : <div className="admin-marketplace-product-list">{products.map((product) => <div className="admin-marketplace-product-row" key={product.id}><div><strong>{product.name}</strong><small>{product.category_name} · {product.sku} · {money(product.price, product.currency)}</small></div><div className="admin-marketplace-row-actions"><Badge variant="outline" className={product.is_active ? "marketplace-active-badge" : "marketplace-inactive-badge"}>{product.is_active ? "Published" : "Draft"}</Badge><span>{product.stock_quantity} stock</span><Button variant="outline" type="button" onClick={() => editProduct(product)}>Edit</Button></div></div>)}</div>}</Card></section>}

        {tab === "orders" && <Card className="panel admin-marketplace-orders-card"><p className="eyebrow">FULFILLMENT QUEUE</p><h2>Marketplace orders</h2>{orders.length === 0 ? <div className="marketplace-empty"><PackageOpen size={24} /><p>No orders have been placed yet.</p></div> : <div className="admin-marketplace-order-list">{orders.map((order) => <article className="admin-marketplace-order-row" key={order.id}><div><p className="marketplace-order-id">#{order.id.slice(0, 8)} · {new Date(order.created_at).toLocaleString("en-BD")}</p><h3>{order.user_name || order.shipping_name} <span>· {order.shipping_city}</span></h3><p>{order.items.map((item) => `${item.product_name} × ${item.quantity}`).join(", ")}</p><small>{order.shipping_phone} · {order.shipping_address}</small></div><div className="admin-marketplace-order-controls"><strong>{money(order.total, order.currency)}</strong><select value={order.status} onChange={(event) => void updateOrder(order, event.target.value)} disabled={busy === order.id}>{statuses.map((status) => <option key={status} value={status}>{status}</option>)}</select><Badge variant="outline">{order.status}</Badge></div></article>)}</div>}</Card>}
      </>}
    </main>
  );
}
