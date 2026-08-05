import {

  Callout,

  Card,

  CardBody,

  CardHeader,

  Grid,

  H1,

  Row,

  Stack,

  Stat,

  Table,

  Text,

  useHostTheme,

} from "cursor/canvas";



// Fill from: python wow_drop_analysis/wow_drop_player_handoff.py --aid AID --date YYYY-MM-DD

const DATA = {

  aid: "AID",

  email: "email",

  name: "Player Name",

  agent: "Agent",

  reportDate: "YYYY-MM-DD",

  titleWeekday: "Monday",

  mondayDelta: "$0",

  pendingRedeem: "$0",

  redeemId: "0",

  pendingSubmitted: "Weekday, D Mon YYYY HH:MM",

  lifetimePurchased: "$0",

  totalRedeemed: "$0",

  totalRedeemedDate: "D Mon YYYY",

  holdPct: "0.0%",

  bonusesPct: "0.0%",

  purchased7d: "$0",

  purchased14d: "$0",

  purchased30d: "$0",

  priorWeekdayLabel: "Monday, 1 Jun 2026",

  thisWeekdayLabel: "Monday, 8 Jun 2026",

  priorWeekday: "$0",

  thisWeekday: "$0",

  restOfWeek: "$0",

  restOfWeekLabel: "Tue to Sun 2 to 7 Jun",

  failedOrderAttempts: 0,

  actionText: "Agent action here.",

  contextLeftTitle: "Context Left",

  contextLeftRows: [["Metric", "Value"]] as [string, string][],

  contextLeftNote: "",

  contextRightTitle: "Context Right",

  contextRightRows: [["Metric", "Value"]] as [string, string][],

  contextRightNote: "",

};



export default function WowDropHandoff() {

  const theme = useHostTheme();

  const sectionTitle = {
    color: theme.text.primary,
    fontWeight: 600,
    fontSize: 14,
  };

  return (

    <Stack gap={10} style={{ padding: 20, maxWidth: 820, background: theme.bg.editor }}>

      <Stack gap={2}>

        <H1>{DATA.titleWeekday} WoW Drop Reason</H1>

        <Text tone="tertiary" size="small">

          {DATA.name} | AID {DATA.aid} | {DATA.email} | For {DATA.agent}

        </Text>

      </Stack>



      {DATA.pendingRedeem && DATA.pendingRedeem !== "$0" && (

        <Row

          gap={10}

          style={{

            padding: "8px 12px",

            borderRadius: 8,

            background: theme.fill.secondary,

            border: `1px solid ${theme.stroke.secondary}`,

            alignItems: "center",

            flexWrap: "wrap",

          }}

        >

          <Text size="small" tone="secondary">Pending Redeem</Text>

          <Text weight="bold" style={{ fontSize: 18, color: theme.accent.primary }}>

            {DATA.pendingRedeem}

          </Text>

          <Text tone="secondary" size="small">

            ID {DATA.redeemId} | {DATA.pendingSubmitted}

          </Text>

        </Row>

      )}



      <Callout tone="warning" title={`Action For ${DATA.agent}`}>

        {DATA.actionText}

      </Callout>



      <Grid columns={2} gap={10} style={{ alignItems: "start" }}>

        <Card>

          <CardHeader style={sectionTitle}>Player Metrics</CardHeader>

          <CardBody>

            <Grid columns={2} gap={8}>

              <Stat label="Lifetime Purchased" value={DATA.lifetimePurchased} tone="info" />

              <Stat label={`Redeemed, ${DATA.totalRedeemedDate}`} value={DATA.totalRedeemed} />

              <Stat label="Hold %" value={DATA.holdPct} tone="success" />

              <Stat label="Bonuses %" value={DATA.bonusesPct} tone="info" />

            </Grid>

            <Table

              headers={["", "7 Days", "14 Days", "30 Days"]}

              rows={[["Purchased", DATA.purchased7d, DATA.purchased14d, DATA.purchased30d]]}

              columnAlign={["left", "right", "right", "right"]}

              striped={false}

              style={{ marginTop: 8 }}

            />

          </CardBody>

        </Card>



        <Card>

          <CardHeader style={sectionTitle}>{DATA.titleWeekday} Purchased WoW Drop</CardHeader>

          <CardBody>

            <Table

              headers={["Period", "Purchased"]}

              rows={[

                [DATA.thisWeekdayLabel, DATA.thisWeekday],

                [DATA.priorWeekdayLabel, DATA.priorWeekday],

                [DATA.restOfWeekLabel, DATA.restOfWeek],

                ["Drop (weekday vs weekday)", DATA.mondayDelta],

              ]}

              columnAlign={["left", "right"]}

              rowTone={["danger", undefined, "success", "danger"]}

              striped

            />

            {DATA.failedOrderAttempts > 0 && (

              <Text size="small" tone="secondary" style={{ marginTop: 6 }}>

                {DATA.failedOrderAttempts} purchase attempts failed {DATA.thisWeekdayLabel} UTC.

              </Text>

            )}

          </CardBody>

        </Card>



        <Card>

          <CardHeader style={sectionTitle}>{DATA.contextLeftTitle}</CardHeader>

          <CardBody>

            <Table

              headers={["Metric", "Value"]}

              rows={DATA.contextLeftRows}

              columnAlign={["left", "right"]}

              striped

            />

            {DATA.contextLeftNote && (

              <Text tone="secondary" size="small" style={{ marginTop: 6 }}>

                {DATA.contextLeftNote}

              </Text>

            )}

          </CardBody>

        </Card>



        <Card>

          <CardHeader style={sectionTitle}>{DATA.contextRightTitle}</CardHeader>

          <CardBody>

            <Table

              headers={DATA.contextRightRows[0]?.length === 3 ? ["When", "Amount", "Status"] : ["Metric", "Value"]}

              rows={DATA.contextRightRows}

              columnAlign={

                DATA.contextRightRows[0]?.length === 3

                  ? (["left", "right", "left"] as const)

                  : (["left", "right"] as const)

              }

              striped

            />

            {DATA.contextRightNote && (

              <Text tone="secondary" size="small" style={{ marginTop: 6 }}>

                {DATA.contextRightNote}

              </Text>

            )}

          </CardBody>

        </Card>

      </Grid>



      <Text tone="quaternary" size="small">

        Source: BigQuery | report date {DATA.reportDate}

      </Text>

    </Stack>

  );

}

