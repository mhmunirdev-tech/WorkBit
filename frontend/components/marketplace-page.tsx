"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { ArrowRight, Copy, Minus, PackageOpen, Plus, RefreshCw, Search, ShoppingBag, Trash2 } from "lucide-react";
import { api } from "../lib/api";
import { showToast } from "../lib/toast";
import { Shell } from "./shell";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";

type Category = { id: string; name: string; slug: string; description: string; product_count: number };
type Product = {
  id: string;
  category_id: string;
  category_name: string;
  category_slug: string;
  sku: string;
  name: string;
  slug: string;
  description: string;
  image_url: string | null;
  image_url_2: string | null;
  image_url_3: string | null;
  video_url: string | null;
  price: string;
  currency: string;
  stock_quantity: number;
  featured: boolean;
};
type CartItem = {
  id: string;
  product_id: string;
  product_name: string;
  slug: string;
  image_url: string | null;
  price: string;
  currency: string;
  stock_quantity: number;
  quantity: number;
  line_total: string;
};
type Cart = { items: CartItem[]; subtotal: string; currency: string };
type AffiliateLink = { referral_code: string; url: string };
type Order = {
  id: string;
  status: string;
  total: string;
  currency: string;
  shipping_city: string;
  created_at: string;
  items: { product_name: string; quantity: number; line_total: string }[];
};
type CheckoutForm = {
  shipping_name: string;
  shipping_phone: string;
  shipping_address: string;
  shipping_city: string;
  customer_note: string;
};

const emptyCheckout: CheckoutForm = {
  shipping_name: "",
  shipping_phone: "",
  shipping_address: "",
  shipping_city: "",
  customer_note: "",
};

function money(value: string | number, currency = "BDT") {
  return new Intl.NumberFormat("en-BD", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(value));
}

function ProductArtwork({ product }: { product: Product | CartItem }) {
  const extraMedia = "video_url" in product ? [product.image_url_2, product.image_url_3].filter(Boolean) : [];
  const images = [product.image_url, ...extraMedia].filter((url): url is string => Boolean(url));
  const videoUrl = "video_url" in product ? product.video_url : null;
  if (!images.length && !videoUrl) {
    return <div className="marketplace-product-art" aria-hidden="true"><ShoppingBag size={30} /></div>;
  }
  return <div className="marketplace-product-media">{images.length > 0 ? <img className="marketplace-product-image" src={images[0]} alt="" /> : <video className="marketplace-product-video" src={videoUrl || undefined} muted playsInline controls preload="metadata" />}{images.length > 1 && <div className="marketplace-product-thumbnails">{images.slice(1).map((image) => <img key={image} src={image} alt="" />)}</div>}{videoUrl && images.length > 0 && <video className="marketplace-product-video" src={videoUrl} muted playsInline controls preload="metadata" />}</div>;
}

function MarketplaceContent() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [cart, setCart] = useState<Cart>({ items: [], subtotal: "0", currency: "BDT" });
  const [orders, setOrders] = useState<Order[]>([]);
  const [affiliateLink, setAffiliateLink] = useState<AffiliateLink | null>(null);
  const [referralCode, setReferralCode] = useState("");
  const [productSlug, setProductSlug] = useState("");
  const [activeCategory, setActiveCategory] = useState("");
  const [search, setSearch] = useState("");
  const [view, setView] = useState<"shop" | "cart" | "orders">("shop");
  const [checkout, setCheckout] = useState<CheckoutForm>(emptyCheckout);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [categoryData, productData, cartData, orderData, affiliateData] = await Promise.all([
        api<Category[]>("/marketplace/categories"),
        api<Product[]>("/marketplace/products"),
        api<Cart>("/marketplace/cart"),
        api<Order[]>("/marketplace/orders"),
        api<AffiliateLink>("/marketplace/referral-link"),
      ]);
      setCategories(categoryData);
      setProducts(productData);
      setCart(cartData);
      setOrders(orderData);
      setAffiliateLink(affiliateData);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Marketplace data could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const incomingCode = params.get("ref") || params.get("referral") || "";
    const incomingProduct = params.get("product") || "";
    try {
      const savedCode = window.localStorage.getItem("workbit:marketplace-referral") || "";
      setReferralCode(incomingCode.trim().toUpperCase() || savedCode.toUpperCase());
      if (incomingCode.trim()) window.localStorage.setItem("workbit:marketplace-referral", incomingCode.trim().toUpperCase());
    } catch {
      setReferralCode(incomingCode.trim().toUpperCase());
    }
    setProductSlug(incomingProduct.trim().toLowerCase());
  }, []);

  const visibleProducts = useMemo(() => {
    const query = search.trim().toLowerCase();
    return products.filter((product) =>
      (!activeCategory || product.category_slug === activeCategory) &&
      (!productSlug || product.slug === productSlug) &&
      (!query || `${product.name} ${product.description}`.toLowerCase().includes(query)),
    );
  }, [activeCategory, productSlug, products, search]);

  async function copyReferralLink(product?: Product) {
    try {
      const link = product
        ? await api<AffiliateLink>(`/marketplace/referral-link?product=${encodeURIComponent(product.slug)}`)
        : affiliateLink;
      if (!link) return;
      await navigator.clipboard.writeText(link.url);
      showToast({ title: "Affiliate link copied", description: "Share this product link and earn 5% in WBC after a successful delivery.", variant: "success" });
    } catch (reason) {
      showToast({ title: "Could not copy link", description: reason instanceof Error ? reason.message : "Select and copy the link manually.", variant: "destructive" });
    }
  }

  async function addToCart(product: Product) {
    setBusy(product.id);
    setError("");
    try {
      const nextCart = await api<Cart>("/marketplace/cart/items", {
        method: "POST",
        body: JSON.stringify({ product_id: product.id, quantity: 1 }),
      });
      setCart(nextCart);
      showToast({ title: "Added to cart", description: `${product.name} is ready for checkout.`, variant: "success" });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The product could not be added to your cart.");
    } finally { setBusy(""); }
  }

  async function updateQuantity(item: CartItem, quantity: number) {
    if (quantity < 1 || quantity > item.stock_quantity) return;
    setBusy(item.id);
    try {
      setCart(await api<Cart>(`/marketplace/cart/items/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({ quantity }),
      }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The cart could not be updated.");
    } finally { setBusy(""); }
  }

  async function removeItem(item: CartItem) {
    setBusy(item.id);
    try {
      setCart(await api<Cart>(`/marketplace/cart/items/${item.id}`, { method: "DELETE" }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The cart item could not be removed.");
    } finally { setBusy(""); }
  }

  async function submitOrder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("checkout");
    setError("");
    try {
      await api<Order>("/marketplace/orders", { method: "POST", body: JSON.stringify({ ...checkout, referral_code: referralCode || null }) });
      setCheckout(emptyCheckout);
      await load();
      setView("orders");
      showToast({ title: "Order placed", description: "Your order was sent to the WorkBit team.", variant: "success" });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The order could not be placed.");
    } finally { setBusy(""); }
  }

  return (
    <main className="marketplace-page">
      <header className="marketplace-hero">
        <div>
          <p className="eyebrow">WORKBIT / SHOP</p>
          <h1>Marketplace</h1>
          <p>Share products with your affiliate link and earn 5% in WBC when a referred order is successfully delivered.</p>
        </div>
        <div className="marketplace-hero-actions">
          <Button variant="outline" type="button" onClick={() => void load()} disabled={loading}><RefreshCw size={15} /> Refresh</Button>
          <Button variant="outline" type="button" onClick={() => void copyReferralLink()}><Copy size={15} /> Earn 5% WBC</Button>
          <Button className={view === "orders" ? "primary" : "secondary-button"} type="button" onClick={() => setView("orders")}><PackageOpen size={16} /> My orders</Button>
          <Button className="primary" type="button" onClick={() => setView("cart")}><ShoppingBag size={16} /> Cart ({cart.items.length})</Button>
        </div>
      </header>

      {error && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}
      {loading ? <Card className="panel marketplace-empty" aria-busy="true">Loading marketplace…</Card> : (
        <>
          {view === "shop" && <>
            <section className="marketplace-toolbar">
              <div className="marketplace-categories">
                <Button type="button" variant={activeCategory ? "outline" : "default"} onClick={() => setActiveCategory("")}>All products</Button>
                {categories.map((category) => <Button key={category.id} type="button" variant={activeCategory === category.slug ? "default" : "outline"} onClick={() => setActiveCategory(category.slug)}>{category.name} <span>{category.product_count}</span></Button>)}
              </div>
              <label className="marketplace-search"><Search size={16} /><Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search products" aria-label="Search products" /></label>
            </section>
            {visibleProducts.length === 0 ? <Card className="panel marketplace-empty"><ShoppingBag size={26} /><h2>No products available yet</h2><p>Products will appear here after the admin publishes the catalog.</p></Card> : <section className="marketplace-product-grid" aria-label="Products">{visibleProducts.map((product) => <Card className="marketplace-product-card" key={product.id}><ProductArtwork product={product} /><div className="marketplace-product-copy"><div className="marketplace-product-meta"><Badge variant="outline">{product.category_name}</Badge>{product.featured && <Badge>Featured</Badge>}</div><h2>{product.name}</h2><p>{product.description || "A useful WorkBit marketplace product."}</p><div className="marketplace-product-footer"><strong>{money(product.price, product.currency)}</strong><span>{product.stock_quantity} in stock</span></div><Button className="primary marketplace-add-button" type="button" onClick={() => void addToCart(product)} disabled={busy === product.id || product.stock_quantity < 1}>{busy === product.id ? "Adding…" : product.stock_quantity < 1 ? "Out of stock" : "Add to cart"} <ArrowRight size={15} /></Button><Button className="marketplace-share-button" variant="outline" type="button" onClick={() => void copyReferralLink(product)}><Copy size={14} /> Share & earn 5% WBC</Button></div></Card>)}</section>}
          </>}

          {view === "cart" && <section className="marketplace-cart-layout"><Card className="panel marketplace-cart-panel"><div className="marketplace-section-heading"><div><p className="eyebrow">YOUR CART</p><h2>{cart.items.length ? `${cart.items.length} product${cart.items.length === 1 ? "" : "s"}` : "Cart is empty"}</h2></div><Button variant="link" type="button" onClick={() => setView("shop")}>Continue shopping <ArrowRight size={14} /></Button></div>{cart.items.length === 0 ? <div className="marketplace-empty"><ShoppingBag size={26} /><p>Add a product before checkout.</p><Button className="primary" type="button" onClick={() => setView("shop")}>Browse products</Button></div> : <div className="marketplace-cart-list">{cart.items.map((item) => <div className="marketplace-cart-item" key={item.id}><ProductArtwork product={item} /><div><h3>{item.product_name}</h3><p>{money(item.price, item.currency)} each</p><div className="marketplace-quantity"><Button variant="outline" size="icon" type="button" onClick={() => void updateQuantity(item, item.quantity - 1)} disabled={busy === item.id || item.quantity <= 1}><Minus size={14} /></Button><strong>{item.quantity}</strong><Button variant="outline" size="icon" type="button" onClick={() => void updateQuantity(item, item.quantity + 1)} disabled={busy === item.id || item.quantity >= item.stock_quantity}><Plus size={14} /></Button></div></div><strong>{money(item.line_total, item.currency)}</strong><Button variant="ghost" size="icon" type="button" aria-label={`Remove ${item.product_name}`} onClick={() => void removeItem(item)} disabled={busy === item.id}><Trash2 size={16} /></Button></div>)}</div>}</Card>{cart.items.length > 0 && <Card className="panel marketplace-checkout-card"><p className="eyebrow">CHECKOUT</p><h2>Delivery details</h2><form className="marketplace-checkout-form" onSubmit={(event) => void submitOrder(event)}><label>Full name<Input required value={checkout.shipping_name} onChange={(event) => setCheckout({ ...checkout, shipping_name: event.target.value })} /></label><label>Phone number<Input required value={checkout.shipping_phone} onChange={(event) => setCheckout({ ...checkout, shipping_phone: event.target.value })} /></label><label>City<Input required value={checkout.shipping_city} onChange={(event) => setCheckout({ ...checkout, shipping_city: event.target.value })} /></label><label>Address<Textarea required rows={3} value={checkout.shipping_address} onChange={(event) => setCheckout({ ...checkout, shipping_address: event.target.value })} /></label><label>Order note (optional)<Textarea rows={2} value={checkout.customer_note} onChange={(event) => setCheckout({ ...checkout, customer_note: event.target.value })} /></label><div className="marketplace-total"><span>Total</span><strong>{money(cart.subtotal, cart.currency)}</strong></div><p className="marketplace-payment-note">Payment method: Cash on delivery. Online payment can be added after the catalog workflow is validated.</p><Button className="primary" type="submit" disabled={busy === "checkout"}>{busy === "checkout" ? "Placing order…" : "Place order"} <ArrowRight size={15} /></Button></form></Card>}</section>}

          {view === "orders" && <Card className="panel marketplace-orders-panel"><div className="marketplace-section-heading"><div><p className="eyebrow">ORDER HISTORY</p><h2>Your marketplace orders</h2></div><Button variant="link" type="button" onClick={() => setView("shop")}>Browse products <ArrowRight size={14} /></Button></div>{orders.length === 0 ? <div className="marketplace-empty"><PackageOpen size={26} /><p>You have not placed a marketplace order yet.</p></div> : <div className="marketplace-order-list">{orders.map((order) => <article className="marketplace-order" key={order.id}><div><p className="marketplace-order-id">#{order.id.slice(0, 8)}</p><h3>{order.items.map((item) => `${item.product_name} × ${item.quantity}`).join(", ")}</h3><p>{new Date(order.created_at).toLocaleDateString("en-BD")} · {order.shipping_city}</p></div><div className="marketplace-order-status"><Badge variant="outline">{order.status}</Badge><strong>{money(order.total, order.currency)}</strong></div></article>)}</div>}</Card>}
        </>
      )}
    </main>
  );
}

export function MarketplacePage() {
  return <Shell><MarketplaceContent /></Shell>;
}
