# Caption content-type labels: guide

Each caption can have **several** labels. Label what the caption **says**, not what the picture shows.

| Label | Use it when the caption… | Examples |
|---|---|---|
| `offer` | announces a discount, sale, deal, bundle or free delivery | "Flat 20% off", "Buy 2 get 1", "Free delivery this week" |
| `new_arrival` | presents something new, a new collection, a restock | "New collection is live", "Back in stock" |
| `price` | states a price | "Rs 2,499", "PKR 1500 only", "Price: 999/-" |
| `call_to_order` | tells the customer how to order or contact | "DM to order", "WhatsApp 03xx…", "Order now via link in bio", "COD available" |
| `product_details` | describes the product: material, size, colours, finish, care | "925 silver", "anti-tarnish", "available in 3 colours" |
| `giveaway` | runs a contest or giveaway | "Giveaway! Follow and tag 2 friends" |
| `review` | shows customer feedback, a delivered order, a happy customer | "Customer love ❤️", "Delivered to Lahore" |
| `styling_tips` | teaches how to wear, style or care for jewellery | "3 ways to style a choker" |
| `behind_the_scenes` | shows making, packing, the shop or the team | "Packing your orders", "How our kundan is made" |
| `event_season` | ties the post to an event or season | "Eid collection", "wedding season", "Valentine's" |
| `other` | none of the above (only a greeting, a quote, emojis, or hashtags) | "✨✨", "Good morning" |

**Language** (one): `english`, `roman_urdu` (Urdu in English letters), `urdu_script`, `mixed`, `none`.

## How the file works
`captions_labels.csv` columns:
- `caption_id`, `caption` (hashtags removed for reading; the full caption is in the posts dataset)
- `labels_draft` (labels separated by `|`) and `language_draft`: **drafted by Claude**
- `labels_verified` and `language_verified`: **filled in by you**. Leave a cell **empty** if you agree with the draft; write the correct labels if you don't.
- `label_source` = `claude_draft` until verified.

The number of rows you change is reported in the FYP as the draft's error rate, which shows the check was real.
