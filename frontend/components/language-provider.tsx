"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

export type Language = "en" | "bn";

const translations: Record<string, string> = {
  "Dashboard": "ড্যাশবোর্ড",
  "Explore offers": "অফার দেখুন",
  "Earning packages": "আর্নিং প্যাকেজ",
  "Ranks": "র‍্যাঙ্ক",
  "Wallet": "ওয়ালেট",
  "Reward history": "রিওয়ার্ড ইতিহাস",
  "Profile": "প্রোফাইল",
  "Settings": "সেটিংস",
  "YOUR SPACE": "আপনার অ্যাকাউন্ট",
  "Your Rewards": "আপনার রিওয়ার্ড",
  "Earned today": "আজকের আয়",
  "Earning balance": "আয়ের ব্যালেন্স",
  "Pending balance": "পেন্ডিং ব্যালেন্স",
  "Total wallet balance": "মোট ওয়ালেট ব্যালেন্স",
  "Deposit balance": "ডিপোজিট ব্যালেন্স",
  "Lifetime earned": "সর্বমোট আয়",
  "Lifetime withdrawn": "সর্বমোট উত্তোলন",
  "Find your next task": "আপনার পরবর্তী কাজ খুঁজুন",
  "Availability and rewards depend on offer terms and provider verification.": "অফারের শর্ত, যোগ্যতা এবং provider-এর যাচাই অনুযায়ী অফার ও রিওয়ার্ড পরিবর্তিত হতে পারে।",
  "Estimated user reward": "আপনার সম্ভাব্য রিওয়ার্ড",
  "Provider payout": "Provider-এর payout",
  "How to qualify": "যোগ্যতার শর্ত",
  "Reward confirmation": "রিওয়ার্ড নিশ্চিতকরণ",
  "A displayed reward is an estimate, not a payment guarantee.": "দেখানো রিওয়ার্ডটি একটি অনুমান; পেমেন্ট নিশ্চিত নয়।",
  "A provider must confirm completion before WorkBit can credit a reward.": "WorkBit রিওয়ার্ড যোগ করার আগে provider-কে completion নিশ্চিত করতে হবে।",
  "The provider or review process did not approve this offer reward.": "Provider বা review প্রক্রিয়া এই অফার রিওয়ার্ড অনুমোদন করেনি।",
  "Your offer reward is waiting for provider confirmation.": "আপনার অফার রিওয়ার্ড provider-এর নিশ্চিতকরণের অপেক্ষায় আছে।",
  "Your offer reward has been approved and added to your available balance.": "আপনার অফার রিওয়ার্ড অনুমোদিত হয়েছে এবং available balance-এ যোগ হয়েছে।",
  "Your offer reward is waiting for a manual review.": "আপনার অফার রিওয়ার্ড manual review-এর অপেক্ষায় আছে।",
  "This reward was reversed. Check reward history for details.": "এই রিওয়ার্ডটি বাতিল করা হয়েছে। বিস্তারিত জানতে reward history দেখুন।",
  "This reward was charged back. Check reward history for details.": "এই রিওয়ার্ডটি chargeback হয়েছে। বিস্তারিত জানতে reward history দেখুন।",
  "This reward was not approved after review.": "Review-এর পর এই রিওয়ার্ড অনুমোদিত হয়নি।",
  "Reward pending": "রিওয়ার্ড অপেক্ষমাণ",
  "Reward approved": "রিওয়ার্ড অনুমোদিত",
  "Reward not approved": "রিওয়ার্ড অনুমোদিত হয়নি",
  "Reward under review": "রিওয়ার্ড পর্যালোচনাধীন",
  "Reward reversed": "রিওয়ার্ড বাতিল",
  "Notifications": "নোটিফিকেশন",
  "No reward updates yet.": "এখনো কোনো রিওয়ার্ড আপডেট নেই।",
  "Mark as read": "পড়া হয়েছে",
  "View reward history": "রিওয়ার্ড ইতিহাস দেখুন",
  "Reversal reason": "বাতিলের কারণ",
  "View details": "বিস্তারিত দেখুন",
  "Language": "ভাষা",
  "English": "English",
  "বাংলা": "বাংলা",
  "Withdrawable balance": "উত্তোলনযোগ্য ব্যালেন্স",
  "Withdrawal Policy": "উত্তোলন নীতিমালা",
  "Only available earning balance can be withdrawn.": "শুধু available earning balance উত্তোলন করা যাবে।",
  "Deposit balance is reserved for packages and is not withdrawable.": "ডিপোজিট ব্যালেন্স প্যাকেজের জন্য সংরক্ষিত, এটি উত্তোলনযোগ্য নয়।",
  "Pending rewards are not withdrawable.": "Pending রিওয়ার্ড উত্তোলন করা যাবে না।",
  "Withdrawal requests are manually reviewed; processing time may vary.": "উত্তোলনের অনুরোধ ম্যানুয়ালি পর্যালোচনা করা হয়; সময় ভিন্ন হতে পারে।",
  "No fixed payout timeline is promised.": "নির্দিষ্ট payout সময়ের নিশ্চয়তা দেওয়া হয় না।",
  "WORKBIT UPDATES": "WORKBIT আপডেট",
  "Announcements": "ঘোষণা",
  "Here’s your verified WorkBit activity at a glance.": "আপনার যাচাইকৃত WorkBit কার্যক্রম এক নজরে দেখুন।",
  "Total earnings": "মোট আয়",
  "Total withdrawn": "মোট উত্তোলন",
  "Approved ledger credits": "অনুমোদিত লেজার ক্রেডিট",
  "Recorded by WorkBit": "WorkBit-এ নথিভুক্ত",
  "Completed wallet movements": "সম্পন্ন ওয়ালেট লেনদেন",
  "Your referrals": "আপনার রেফারেল",
  "Total referrals": "মোট রেফারেল",
  "Package members": "প্যাকেজ সদস্য",
  "Referral income": "রেফারেল আয়",
  "OFFER CATALOG": "অফার ক্যাটালগ",
  "OFFER REQUIREMENTS": "অফারের শর্ত",
  "Reward estimate unavailable until a policy is configured.": "Reward policy সেট না করা পর্যন্ত সম্ভাব্য রিওয়ার্ড দেখানো যাবে না।",
  "Back to home": "হোমে ফিরে যান",
  "Withdrawal help": "উত্তোলন সংক্রান্ত তথ্য",
  "Deposit": "ডিপোজিট",
  "Withdraw": "উত্তোলন",
  "WorkBit": "WorkBit",
  "Complete the offer requirements to earn a reward.": "রিওয়ার্ড পেতে অফারের শর্ত পূরণ করুন।",
  "PARTNER OFFERS": "পার্টনার অফার",
  "More ways to earn": "আয়ের আরও সুযোগ",
  "Browse available offers without leaving WorkBit. Eligibility and final rewards depend on each offer's terms.": "WorkBit ছাড়াই উপলভ্য অফার দেখুন। যোগ্যতা ও চূড়ান্ত রিওয়ার্ড প্রতিটি অফারের শর্তের ওপর নির্ভরশীল।",
  "How to qualify:": "যোগ্যতার শর্ত:",
  "Start offer": "অফার শুরু করুন",
  "May vary by completion": "সম্পন্ন করার ধরন অনুযায়ী পরিবর্তিত হতে পারে",
  "Rewards shown are estimated from WorkBit's active reward policy. Provider verification is required before rewards are credited.": "দেখানো রিওয়ার্ড WorkBit-এর বর্তমান policy অনুযায়ী অনুমান করা হয়েছে। রিওয়ার্ড যোগের আগে provider-এর যাচাই প্রয়োজন।",
  "INVITE YOUR NETWORK": "পরিচিতদের আমন্ত্রণ জানান",
  "Offer details": "অফারের বিস্তারিত",
  "Back to offers": "অফারে ফিরে যান",
  "Estimated time": "আনুমানিক সময়",
  "Difficulty": "কঠিনতার মাত্রা",
  "Availability": "উপলভ্যতা",
  "minutes": "মিনিট",
  "Varies by task": "কাজভেদে ভিন্ন হতে পারে",
  "Development test offer. The estimated user reward applies the active WorkBit reward policy to the displayed provider payout.": "এটি উন্নয়নমূলক পরীক্ষার অফার। দেখানো provider payout-এ WorkBit-এর বর্তমান reward policy প্রয়োগ করে আপনার সম্ভাব্য রিওয়ার্ড হিসাব করা হয়েছে।",
};

type LanguageContextValue = {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (text: string) => string;
};

const LanguageContext = createContext<LanguageContextValue>({
  language: "en",
  setLanguage: () => undefined,
  t: (text) => text,
});

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<Language>("en");

  useEffect(() => {
    const saved = window.localStorage.getItem("workbit-language");
    if (saved === "bn" || saved === "en") setLanguageState(saved);
  }, []);

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  const setLanguage = useCallback((value: Language) => {
    window.localStorage.setItem("workbit-language", value);
    setLanguageState(value);
  }, []);
  const t = useCallback(
    (text: string) => language === "bn" ? translations[text] ?? text : text,
    [language],
  );
  const value = useMemo(() => ({ language, setLanguage, t }), [language, setLanguage, t]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  return useContext(LanguageContext);
}
