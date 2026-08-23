/** Weekday CRM offer calendar — synced from crm_offer_calendar/data/current_offers.json.
 *  Update this file when the monthly plan changes (no BigQuery). */
export interface CrmOfferCell {
  day: string;
  campaign: string;
  lead: string;
  lead_low: number;
  follow_label?: string;
  follow_value?: string;
  link?: string;
  link_label?: string;
}

export interface CrmOfferCycle {
  title: string;
  note?: string;
  cells: CrmOfferCell[];
}

export interface CrmOffersData {
  title: string;
  subtitle: string;
  cycles: CrmOfferCycle[];
}

export const CRM_DAY_ORDER = [
  "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
] as const;

export const CRM_BANDS = [
  { id: "40plus", label: "40% and above", min: 40, hue: "#1f8a65", rgb: "31,138,101" },
  { id: "30to39", label: "30% to 39%", min: 30, hue: "#3685bf", rgb: "54,133,191" },
  { id: "20to29", label: "20% to 29%", min: 20, hue: "#c08532", rgb: "192,133,50" },
  { id: "below20", label: "Below 20%", min: 0, hue: "#db704b", rgb: "219,112,75" },
] as const;

export const CRM_OFFERS: CrmOffersData = {
  title: "Jackpota Monthly Calendar: Top Offers (Seg 4-6)",
  subtitle: "The month's biggest campaigns by weekday, in two cycles that alternate through the month.",
  cycles: [
    {
      title: "Cycle A",
      note: "First rotation",
      cells: [
        { day: "Sunday", campaign: "4 Offers", lead: "40% or 50%", lead_low: 40,
          follow_label: "Offers avg", follow_value: "22%",
          link: "https://docs.google.com/spreadsheets/d/1qclsPpxzzfnsQgFq2pnjqh7jVX4omg82AKzEGATy1F8/edit?gid=1754602509",
          link_label: "Daily CRM Campaigns" },
        { day: "Monday", campaign: "Extra Vaganza", lead: "10% or 30%", lead_low: 10,
          follow_label: "Offers avg", follow_value: "18%",
          link: "https://docs.google.com/spreadsheets/d/1sBfML6gMANSOkYeprMRgyeXqi6PxhcnOwiIJg9c4Il0/edit?gid=1278151603",
          link_label: "Gaming Features Campaigns" },
        { day: "Tuesday", campaign: "3 Offers", lead: "40%", lead_low: 40,
          follow_label: "Offers avg", follow_value: "24%",
          link: "https://docs.google.com/spreadsheets/d/1qclsPpxzzfnsQgFq2pnjqh7jVX4omg82AKzEGATy1F8/edit?gid=1256512071",
          link_label: "Daily CRM Campaigns" },
        { day: "Wednesday", campaign: "Extra SC on 3rd & 5th", lead: "26% to 40%", lead_low: 26,
          follow_label: "Offers avg", follow_value: "30%",
          link: "https://docs.google.com/spreadsheets/d/1qclsPpxzzfnsQgFq2pnjqh7jVX4omg82AKzEGATy1F8/edit?gid=1738637755",
          link_label: "Daily CRM Campaigns" },
        { day: "Thursday", campaign: "3 Offers FS", lead: "17% to 24%", lead_low: 17,
          follow_label: "Offers avg", follow_value: "20%",
          link: "https://docs.google.com/spreadsheets/d/1qclsPpxzzfnsQgFq2pnjqh7jVX4omg82AKzEGATy1F8/edit?gid=1244995399",
          link_label: "Daily CRM Campaigns" },
        { day: "Friday", campaign: "Lucky or Safe", lead: "20%", lead_low: 20,
          follow_label: "Boost up to", follow_value: "100%",
          link: "https://docs.google.com/spreadsheets/d/1sBfML6gMANSOkYeprMRgyeXqi6PxhcnOwiIJg9c4Il0/edit?gid=338455526",
          link_label: "Gaming Features Campaigns" },
        { day: "Saturday", campaign: "4 Offers + FS", lead: "43%", lead_low: 43,
          follow_label: "Offers avg", follow_value: "25%",
          link: "https://docs.google.com/spreadsheets/d/1qclsPpxzzfnsQgFq2pnjqh7jVX4omg82AKzEGATy1F8/edit?gid=1708019590",
          link_label: "Daily CRM Campaigns" },
      ],
    },
    {
      title: "Cycle B",
      note: "Second rotation",
      cells: [
        { day: "Sunday", campaign: "3 Offers", lead: "40%", lead_low: 40,
          follow_label: "Offers avg", follow_value: "24%",
          link: "https://docs.google.com/spreadsheets/d/1qclsPpxzzfnsQgFq2pnjqh7jVX4omg82AKzEGATy1F8/edit?gid=1256512071",
          link_label: "Daily CRM Campaigns" },
        { day: "Monday", campaign: "Same Package, More FS", lead: "15%", lead_low: 15,
          follow_label: "Boost up to", follow_value: "31%",
          link: "https://docs.google.com/spreadsheets/d/1qclsPpxzzfnsQgFq2pnjqh7jVX4omg82AKzEGATy1F8/edit?gid=1476381756",
          link_label: "Daily CRM Campaigns" },
        { day: "Tuesday", campaign: "50% Extra on 3rd Purchase", lead: "16%", lead_low: 16,
          follow_label: "Boost up to", follow_value: "50%",
          link: "https://docs.google.com/spreadsheets/d/1qclsPpxzzfnsQgFq2pnjqh7jVX4omg82AKzEGATy1F8/edit?gid=1738637755",
          link_label: "Daily CRM Campaigns" },
        { day: "Wednesday", campaign: "4 Offers + FS", lead: "20% to 25%", lead_low: 20,
          link: "https://docs.google.com/spreadsheets/d/1qclsPpxzzfnsQgFq2pnjqh7jVX4omg82AKzEGATy1F8/edit?gid=622867478",
          link_label: "Daily CRM Campaigns" },
        { day: "Thursday", campaign: "4 Offers", lead: "40% or 50%", lead_low: 40,
          follow_label: "Offers avg", follow_value: "22%",
          link: "https://docs.google.com/spreadsheets/d/1qclsPpxzzfnsQgFq2pnjqh7jVX4omg82AKzEGATy1F8/edit?gid=1754602509",
          link_label: "Daily CRM Campaigns" },
        { day: "Friday", campaign: "2 Offers", lead: "30% to 40%", lead_low: 30,
          link: "https://docs.google.com/spreadsheets/d/1qclsPpxzzfnsQgFq2pnjqh7jVX4omg82AKzEGATy1F8/edit?gid=98024857",
          link_label: "Daily CRM Campaigns" },
        { day: "Saturday", campaign: "3 Offers FS", lead: "17% to 24%", lead_low: 17,
          follow_label: "Offers avg", follow_value: "20%",
          link: "https://docs.google.com/spreadsheets/d/1qclsPpxzzfnsQgFq2pnjqh7jVX4omg82AKzEGATy1F8/edit?gid=1244995399",
          link_label: "Daily CRM Campaigns" },
      ],
    },
  ],
};
