

--CREATE TABLE `silver-social-games-data.temp.Improvado_Topaz_Testing_Dec25` AS
with 
d as 
  (
 
       select 
                  d.account_id      
                        
                        ,case when DATE_DIFF(date, ifnull(ftp_date,'2099-01-01') , DAY)=0 then 'First Day'
                              when DATE_DIFF(date, ifnull(ftp_date,'2099-01-01') , DAY)<=6 then 'First 2-7d'
                              when DATE_DIFF(date, ifnull(ftp_date,'2099-01-01') , DAY)<30 then 'First 8-30d'
                              when DATE_DIFF(date, ifnull(ftp_date,'2099-01-01') , DAY)<90 then 'First 31-90d'
                              when DATE_DIFF(date, ifnull(ftp_date,'2099-01-01') , DAY)<180 then 'First 91-180'
                              when DATE_DIFF(date, ifnull(ftp_date,'2099-01-01') , DAY)<365 then 'First 181-365'
                              when DATE_DIFF(date, ifnull(ftp_date,'2099-01-01') , DAY)>365 then '+1Y'
                              else 'UD' end as Seniority
                        
                        ,ifnull(ftp_date,'2099-01-01') as ftp_date
                  , ifnull((reg_date),'2099-01-01') as reg_date
                  ,ifnull(adgroup_name,'UD') as AdGroupName

                  , case when ifnull(ftp_date,'2099-01-01')<'2099-01-01' then 1 else 0 end as IsFTP
                  ,d.date
                  ,acc.reg_state
                  ,acc.reg_country
                  ,acc.unified_channel

                  -- ,brand               
                        -- ,country
            --       ,count(distinct bonus_type) as numn_BT
            --       --- ,bonus_type   
            --       --,d.date
            --       ,sum(ifnull(profit,0)-ifnull(loss,0)-ifnull(sc_reward_amount,0) ) as NGR
            --       ,sum(coalesce(redeemed,0)) as redeemed
            --       ,sum(coalesce(purchased,0)) as purchased
            --       ,sum(ifnull(purchased,0)-ifnull(redeemed,0)-ifnull(chargeback,0)-ifnull(refunds,0)) as net_purchases

            --       ,sum(ifnull(purchased_num,0)) as purchased_num
            --       ,sum(ifnull(purchased_attempted,0)) as purchased_attempted
            --       ,sum(ifnull(redeemed_num,0)) as redeemed_num
            --       ,sum(ifnull(redeem_created,0)) as redeem_created
            --       ,sum(ifnull(redeemed_amt_confirmed_locked_pre,0)) as redeemed_amt_confirmed_locked_pre
            --       ,sum(ifnull(redeemed_amount_confirmed_on_confirm_date,0)) as redeemed_amount_confirmed_on_confirm_date
            --       ,sum(ifnull(redeem_confirmed_amt,0)) as redeem_confirmed_amt
            --       ,sum(ifnull(cancelled_redeem,0)) as cancelled_redeem 
            --       ,sum(ifnull(spins,0)) as spins
            --       ,sum(ifnull(profit,0)) as Bets
            --       ,sum(ifnull(loss,0)) as Payout
            --       ,sum(ifnull(chargeback,0)) as chargeback

            --       ,sum(ifnull(sc_reward_amount,0)) as sc_reward_amount
            --     --  ,sum(case when bonus_type='Daily Login' then ifnull(sc_reward_amount,0) else 0 end) as sc_reward_amount_DailyLogin
            --     --  ,sum(case when bonus_type='Sign Up' then ifnull(sc_reward_amount,0) else 0 end) as sc_reward_amount_SignUp
            --      -- ,sum(case when bonus_type='freespin' then ifnull(sc_reward_amount,0) else 0 end) as sc_reward_amount_FS
            --      -- ,sum(case when bonus_type='Manual' then ifnull(sc_reward_amount,0) else 0 end) as sc_reward_amount_Manual
            --       ,sum(ifnull(refunds_num,0)) as refunds_num
            --       ,sum(ifnull(refunds,0)) as refunds
            --       ,count(distinct case when coalesce(purchased,0) > 0 then d.date else NULL end ) as APD_Purchase
            --       ,count(distinct case when ifnull(redeem_created,0) > 0 then d.date else NULL end ) as APD_Redeem
            --       ,count(distinct case when coalesce(spins,0) > 0 then d.date else NULL end ) as APD_Active
            --       ,count(distinct case when coalesce(sc_reward_amount,0) > 0 then d.date else NULL end ) as APD_Rewards

                        FROM  `silver-social-games-data.jackpota_agg.daily_player_revenue_kpis` as d
                        left join (         
                                    SELECT a.account_id, max(ftp_date) as ftp_date,max(date(reg_date)) as reg_date 
                                          ,reg_state
                                          ,reg_country
                                          ,unified_channel  
                                          ,adgroup_name 
                                    FROM `silver-social-games-data.dbt_marketing_mart.player_stats_daily` as a
                                          left join (       
                                                      select
                                                                  adgroup_id,
                                                                  adgroup_name,
                                                                  date,
                                                                  RANK() OVER (PARTITION BY adgroup_id ORDER BY date DESC) as ad_rank
                                                      from(
                                                                  select     
                                                                              adgroup_id,
                                                                              max(date) as date,
                                                                              REPLACE(lower(adgroup_name), ' ', '') as   adgroup_name,
                                                                              
                                                                  from `dbt_marketing_mart.singular_daily_cost`
                                                                  where ifnull(adgroup_id,'UD')<>'UD'
                                                                  group by adgroup_id,
                                                                              REPLACE(lower(adgroup_name), ' ', '') 
                                                                  )
                                                      qualify ad_rank=1 and LENGTH(adgroup_id)>1 and LENGTH(adgroup_name)>1
                                                 ) as b  on lower(trim(a.reg_adgroup))=lower(trim(b.adgroup_id))
                                    group by a.account_id
                                          ,reg_state
                                          ,reg_country
                                          ,unified_channel 
                                          ,adgroup_name
                        ) as acc on acc.account_id=d.account_id
                where 
                        d.date between reg_date and   DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
                      --  and d.account_id=57543884

                  group by
                  d.account_id              
                  --    ,brand                  
                  --  ,country                  
                  ,d.date
                  ,acc.reg_state
                        ,acc.reg_country
                        ,acc.unified_channel
                  -- ,bonus_type    
                        ,ifnull(ftp_date,'2099-01-01')
                  , ifnull(reg_date,'2099-01-01')
                  , case when ifnull(ftp_date,'2099-01-01')<'2099-01-01' then 1 else 0 end 
                  ,ifnull(adgroup_name,'UD')
                  ,case when DATE_DIFF(date, ifnull(ftp_date,'2099-01-01') , DAY)=0 then 'First Day'
                              when DATE_DIFF(date, ifnull(ftp_date,'2099-01-01') , DAY)<=6 then 'First 2-7d'
                              when DATE_DIFF(date, ifnull(ftp_date,'2099-01-01') , DAY)<30 then 'First 8-30d'
                              when DATE_DIFF(date, ifnull(ftp_date,'2099-01-01') , DAY)<90 then 'First 31-90d'
                              when DATE_DIFF(date, ifnull(ftp_date,'2099-01-01') , DAY)<180 then 'First 91-180'
                              when DATE_DIFF(date, ifnull(ftp_date,'2099-01-01') , DAY)<365 then 'First 181-365'
                              when DATE_DIFF(date, ifnull(ftp_date,'2099-01-01') , DAY)>365 then '+1Y'
                              else 'UD' end 
                          
 ) 

, Current_VIP as
(
  select   distinct
            account_id
            , JSON_VALUE(tags, '$[0]') AS tagAgent1     
   FROM
  `silver-social-games-data.transactional_data.uam_account_category_tags`  
  where category='Elite'
        and JSON_VALUE(tags, '$[0]')  is not null
)
 , ZendeskAttributesVIP as 
(
      select 
        account_id
        ,requester_name
        ,min(case when lower(agent_email) like '%silver%' then date(created_at) else '2099-01-01' end) as agent_start_mangaed_date
        ,max(case when lower(agent_email) like '%silver%' then date(last_update) else '1990-01-01' end) as last_contact_date
        ,min(case when lower(agent_email) not like '%silver%' then date(created_at) else '2099-01-01' end) as player_first_contact
        ,max(case when lower(agent_email) not like '%silver%' then date(last_update) else '1990-01-01' end) as player_last_contact
      from
        (
        select
          --r.external_id,
          t.id AS ticket_id,
          t.created_at,
          t.status,
          t.requester_id,
          r.name AS requester_name,
          r.email AS requester_email,
          ua.email,
          ua.id as account_id,
          t.assignee_id,
          a.name AS agent_name,
          a.email AS agent_email,
            greatest(t.created_at,t.updated_at) as last_update -- We don't know yer how to find last concat at zen_desk.
        FROM
          `zendesk.ticket` t
        LEFT JOIN 
          `zendesk.user` r
          ON t.requester_id = r.id
        LEFT JOIN 
          `zendesk.user` a
          ON t.assignee_id = a.id
        LEFT JOIN  
          `transactional_data.uam_accounts` ua 
          ON CAST(r.external_id as STRING) = CAST(ua.id as STRING) or r.email=ua.email
        WHERE 
        --  lower(a.email) like '%silver%'
          1=1
          and  ua.id  is not null
        ) as tab
      group by 
          account_id , requester_name
      having max(case when lower(agent_email) like '%silver%' then 1 else 0 end)=1
  ) 
, VIP as 
(
  select distinct
        v.account_id
        ,v.tagAgent1 as agent_name
        ,requester_name as requester_name
        ,agent_start_mangaed_date
        ,last_contact_date
        ,player_first_contact
        ,player_last_contact
      from
             Current_VIP as v 
            inner join ZendeskAttributesVIP z on z.account_id=v.account_id
)


 ,flag as
  (
                  select account_id , min(flagged_from) as First_flagged_from, max(flagged_from) last_flagged_from , max(flagged_to) as last_flagged_to
                        --  ,    case when rn_one=1 then detection_type else 'UD' end as last_detection_type
                       -- , case when rn_two=1 then detection_type else 'UD' end as first_detection_type 
                       , count(*) as num_flagged
                  from
                  (          select 
                              account_id,
                              detection_type,
                              (flagged_from) as flagged_from,
                              flagged_to
                            --  ,rank() over (partition by account_id order by min(flagged_from) desc) as rn_one
                             -- ,rank() over (partition by account_id order by min(flagged_from) asc) as rn_two
                              

                              from `silver-social-games-data.jackpota_agg.scd_adv_players_all` a 
                              where flagged_from>='2024-01-01'
                        group by all
                  ) as flag
                  group by account_id --, case when rn_one=1 then detection_type else 'UD' end , case when rn_two=1 then detection_type else 'UD' end

      ) --as flag on flag.account_id=d.account_id --and date(flagged_from)=(d.date)

   , MC as
                               ( 
                                   select distinct
                                    a.account_id,
                                    b.display_name as network,
                                    case when b.partner_type is not null then b.partner_type when lower(a.unified_channel) in ('crm','direct','unlabelled','brokem from app') then 'Rest' else 'Organic' end as                                       channel_type
                                   from `dbt_marketing_mart.player_stats_daily` a left join `dbt_mappings.combined_partner_mapping` b on lower(trim(a.reg_partnerid))=lower(trim(b.source_id))
                                ) --as MC on MC.account_id=d.account_id

, player_det as
         (
        select distinct
                 ua.id as account_id
                 ,locked_at
                  ,ua.lock_reason_comment
                  ,ua.locked
                  , ua.phone_number
                  ,ua.email
                  --,ua.name
                  ,ua.status as redeem_status
                  ,ua.lock_reason
                  ,ua.internal as test_user
                  ,coalesce(concat(p.first_name,' ',p.last_name),ua.name) as name
                  ,p.first_name
                  ,p.last_name
                  ,string_agg(concat(`hash`,'/',ua.id)) as uuid
                  ,KYC

        from `transactional_data.uam_accounts` as ua
                  left join `transactional_data.uam_persons` p on ua.person_id=p.id
        --where locked
        group by all
        ) --as player_det on player_det.account_id=d.account_id

, players_birth_date as (

            select distinct id as account_id , date_of_birth
            from `transactional_data.uam_account_personal_info` as ua

)
    

,joinbalance as 
(
            select
                  account_id
                  ,ref_date 
                  ,sum(coalesce(amount,0))  as sc_balance
                  ,sum(coalesce(redeemable,0)) as last_redeemable_balance 
                  ,sum(coalesce(unplayed,0)) as last_unplayed_balance 
            from 
                  `silver-social-games-data.jackpota_agg.fact_account_balance_history`
            where 
                  1=1
                  and lower(currency)='sc'
                  and ref_date   =   DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY) 
            group by 
            account_id
                  ,ref_date 
)  --as joinbalance on joinbalance.account_id=d.account_id --and joinbalance.ref_date=d.date


, Sensai as 

(
select  
                  SAFE_CAST( player_ID AS INT64) as account_id_SentSensAI 
                  ,min(date_sent) as First_DateSentSensAI
                  ,Max(date_sent) as Last_DateSentSensAI

                  ,count(*) num_catch_SentSensAI
from `silver-social-games-data.analytics_sensai.sensai_suspected_accounts` 
group by   SAFE_CAST( player_ID AS INT64)
)


----------------------------------------------------------------------------------------------------
----------------------------------------------------------------------------------------------------

 ,LT_calc as 
  (
            select 
                  d.account_id      
                  ,d.date 
                  ,sum(ifnull(profit,0)-ifnull(loss,0)-ifnull(sc_reward_amount,0) ) as NGR
                  ,sum(coalesce(purchased,0)) as purchased
                  ,sum(ifnull(purchased_num,0)) as purchased_num
                  ,sum(ifnull(purchased,0)-ifnull(redeemed_amt_confirmed_locked_pre,0)-ifnull(chargeback,0)-ifnull(refunds,0)) as net_purchases
                  ,sum(ifnull(redeem_created,0)) as redeem_created
                  ,sum(ifnull(spins,0)) as spins
                  ,sum(ifnull(sc_reward_amount,0)) as sc_reward_amount

            FROM  `silver-social-games-data.jackpota_agg.daily_player_revenue_kpis` as d
            where 
                        d.date between  '2024-01-01' and  CURRENT_DATE()-1
             group by
                   d.account_id     
                  ,d.date
 ) 
, LT as(
select * ,SUM(NGR)
                        OVER (
                  PARTITION BY LT_calc.account_id     
                  ORDER BY LT_calc.date asc
                  ) AS NGR_Cummaltive
      ,SUM(net_purchases)
                        OVER (
                  PARTITION BY LT_calc.account_id     
                  ORDER BY LT_calc.date asc
                  ) AS net_purchases_Cummaltive
from LT_calc
)
,MaxValue as 
(
  select  account_id,
          max(NGR_Cummaltive) as max_LT_NGR, 
          max(net_purchases_Cummaltive) as max_LT_NP,
          sum(NGR) as LT_NGR,
          sum(net_purchases) as LT_net_purchases,
          sum(purchased) as LT_purchased,
          sum(purchased_num) as LT_purchased_num
          ,max( case when coalesce(purchased,0) > 0 then date else '1900-01-01' end ) as Last_Purchase_date
          ,max( case when ifnull(redeem_created,0) > 0 then date else '1900-01-01' end ) as  Last_Redeem_date
          ,max( case when coalesce(spins,0) > 0 then date else '1900-01-01' end ) as  Last_Active_date
          ,max( case when coalesce(sc_reward_amount,0) > 0 then date else '1900-01-01' end ) as  Last_Rewards_date
  from LT
  group by 
      account_id
)

, sus as
(
select distinct
      a.id as account_id,
      b.do_not_send_emails,
      b.do_not_send_pushes,
      b.do_not_send_sms,
      b.do_not_call
      
from `transactional_data.uam_accounts` a join `transactional_data.uam_account_preferences` b on a.id=b.id
),


purchases AS (
  SELECT
    p.account_id as account_id_p ,
   -- UA.email as email,
    DATE(p.at) AS purchase_date,
    p.created_at AS purchase_ts,
    h.code AS offer_code,
    p.amount as purchase_amount,
    p.sc_amount as sc_amount,
    p.gc_amount as gc_amount, -- NEW GC field 

    GREATEST(p.sc_amount-p.amount, 0) AS sc_reward_amount,
    row_number() OVER (PARTITION BY p.account_id ORDER BY p.created_at asc) AS rn_LT,
    row_number() OVER (PARTITION BY p.account_id, date(p.created_at) ORDER BY p.created_at asc) AS rn_Daily


  FROM `transactional_data.payment_payment_orders` p 
  LEFT JOIN `transactional_data.payment_offer_templates` h     ON h.id = p.offer_id 

  left join  `transactional_data.uam_accounts` as ua on ua.id = p.account_id
   left join (         
                    SELECT account_id, max(ftp_date) as ftp_date,max(date(reg_date)) as reg_date 
                                          ,reg_state
                                          ,reg_country
                                          ,unified_channel   
                                    FROM `silver-social-games-data.dbt_marketing_mart.player_stats_daily` 
                                    group by account_id
                                          ,reg_state
                                          ,reg_country
                                          ,unified_channel 
                        ) as acc on acc.account_id=p.account_id
  WHERE p.success
--  and p.account_id=57543884
--  --and DATE(p.at)='2025-12-26'
  
  and p.at between acc.ftp_date and DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY) ----- 

 -- order by account_id_p, purchase_ts desc
) , 

Rewards as (

select
account_id ,
    reward_date
  --  ,reward_datetime
    , month_
    ,year_
   -- ,num_rewards as num_rewards_agg
    ,product_title      
    ,campaign_title 
    ,IsFTP            
    --   ,count(distinct account_id) as num_players
    -- ,sum(num_rewards) as num_rewards_total
    ,sum(gold_reward_amount) as gold_reward_amount  -- NEW GC field 
    ,sum(sweepstake_reward_amount) as  sweepstake_reward_amount 

    -- ,sum(loss_sweepstake_amount) as   loss_sweepstake_amount  
    -- ,sum(total_spins) as    total_spins 
    -- ,sum(left_spins) as   left_spins  
    -- ,sum(r.reward_count) as   reward_count


    ,sum(num_rewards) as num_rewards_total
    ,sum(r.reward_count) as   reward_count

from
(   
      SELECT 
      -- reward_id      
        reward_date 
      --  ,reward_datetime
        ,acc.reg_state
        ,acc.reg_country
        ,acc.unified_channel
       , extract(month from reward_date) as month_
      ,extract(year from reward_date) as year_  
      ,case when  extract( year from ifnull(ftp_date,'2099-01-01'))<2099 then 'FTP' else 'Other' end as IsFTP
        ,r.account_id     
        --,product_id     
        --,product_code     
        ,product_title      
        ,product_type     
        --,event_type     
        ,campaign_title     
        --,campaign_category      
        --,campaign_type      
        --,campaign_objective   
        --,count(distinct account_id) as num_players
        -- ,count(distinct reward_id) as num_rewards 
        ,sum(gold_reward_amount) as gold_reward_amount  -- NEW GC field 
        ,sum(sweepstake_reward_amount) as  sweepstake_reward_amount
        -- ,sum(loss_sweepstake_amount) as   loss_sweepstake_amount  
        -- ,sum(total_spins) as    total_spins 
        -- ,sum(left_spins) as   left_spins  
        -- ,sum(r.reward_count) as   reward_count  


     ,count(distinct reward_id) as num_rewards 
     ,sum(r.reward_count) as   reward_count

      FROM `silver-social-games-data.jackpota_agg.fact_rewards`  as r 


           left join (         
                                    SELECT account_id, max(ftp_date) as ftp_date,max(date(reg_date)) as reg_date 
                                          ,reg_state
                                          ,reg_country
                                          ,unified_channel   
                                    FROM `silver-social-games-data.dbt_marketing_mart.player_stats_daily` 

                                   --    where account_id= CID -----------------------------------------------------to remove 
                                    
                                    group by account_id
                                          ,reg_state
                                          ,reg_country
                                          ,unified_channel 
                        ) as acc on acc.account_id=r.account_id
      --where r.reward_date>=Sdate

      where r.reward_date between acc.reg_date and DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
    --  and   r.account_id = 261639596 --CID   -----------------------------------------------------to remove 
      and product_title <> 'Offer Discount Reward'
 --     and r.sweepstake_reward_amount>0 
            --and extract( year from ifnull(ftp_date,'2099-01-01'))<2099
           -- and product_type in ('reward', 'freespin')
      group by 

         acc.reg_state
        ,acc.reg_country
        ,acc.unified_channel
        --reward_id     
        ,reward_date  
        ,reward_datetime
  
         ,extract(month from reward_date) 
        ,extract(year from reward_date) 
        ,r.account_id         
        ,product_id     
        ,product_code     
        ,product_title      
        ,product_type     
        --,event_type     
       ,campaign_title      
       ,case when   extract( year from ifnull(ftp_date,'2099-01-01'))<2099 then 'FTP' else 'Other' end
      -- ,campaign_category     
        --,campaign_type      
        --,campaign_objective   
) as r
group by
account_id,
    reward_date
    --,reward_datetime
  --  ,num_rewards
    ,product_title      
    ,product_type  
    ,campaign_title 
     ,month_
    ,year_
    ,IsFTP) ,

--select * from  rewards left join purchases on rewards.account_id=purchases.account_id_p and purchases.purchase_date=rewards.reward_date --purchases.offer_code=rewards.campaign_title and 

Rewards_U as (

select 
account_id_p as account_id 
,p.purchase_date as reward_date
,p.purchase_ts as reward_datetime -- p.created_at AS purchase_ts,
,'Offer Discount Reward' as product_title
,p.offer_code as campaign_title
,p.purchase_amount
,p.sc_amount
,p.sc_reward_amount
,p.gc_amount as gold_reward_amount -- NEW GC field 
,1 as num_rewards_total
,p.rn_LT as purchase_index_overall
,p.rn_Daily as purchase_index_daily

from  purchases p

Union all

select
r.account_id
,date(reward_date) as reward_date
,TIMESTAMP('2099-01-01 00:00:00') as reward_datetime
,product_title 
,campaign_title
,0 as purchase_amount
,0 as sc_amount
,sum(sweepstake_reward_amount) as sc_reward_amount
,sum(gold_reward_amount) as gold_reward_amount -- NEW GC field 
,sum(num_rewards_total) as num_rewards_total
,0 as purchase_index_overall
,0 as purchase_index_daily

from Rewards r
 group by all ), 

RU1 as ( select  
RU.*,

 MAX(CASE 
        WHEN RU.product_title = 'Offer Discount Reward' 
        THEN RU.purchase_index_overall 
    END) OVER (PARTITION BY RU.account_id ORDER BY RU.reward_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW ) as Cumulative_purchases
from
    Rewards_U RU
)

select RU1.*,

D.Seniority,
D.ftp_date,
D.reg_date,
D.AdGroupName,
D.IsFTP,
D.date,
D.reg_state,
D.reg_country,
D.unified_channel
      -- ,ifnull(purchased,0)-  (ifnull(red_amt,0)-ifnull(Cancllend_Amt,0))
      --       -ifnull(chargeback,0)-ifnull(refunds,0) as net_purchases_ByReq

      ,case when ifnull(flag.account_id,-1)>0 then 'Flagged' else 'No' end as IsFlaggedAbuse
     -- ,ifnull(last_detection_type,'UD') last_detection_type
     -- ,ifnull(first_detection_type,'UD') first_detection_type
      ,ifnull(num_flagged,0) num_flagged
      ,ifnull(First_flagged_from,'1900-01-01') as First_flagged_from
      ,ifnull(last_flagged_from,'1900-01-01') as last_flagged_from
      ,ifnull(last_flagged_to,'1900-01-01') as last_flagged_to

      ,case when ifnull(account_id_SentSensAI,-1)>0 then 1 else 0 end as IsFlaggedSensai
      ,ifnull(num_catch_SentSensAI,0) num_catch_SentSensAI
      ,ifnull(First_DateSentSensAI,'1900-01-01') as First_DateSentSensAI
      ,ifnull(Last_DateSentSensAI,'1900-01-01') as Last_DateSentSensAI

      -- ,(ifnull(red_amt,0)) as red_amt 
      --,(ifnull(Cancllend_Amt,0)) as Cancllend_Amt     
      --,ifnull(red_amt,0)-ifnull(Cancllend_Amt,0) as RedeemReq_Minus_Cancled
     -- ,(ifnull(locked_confirmed_Amt,0)) as locked_confirmed_Amt   
     -- ,(ifnull(pre_authorized_Amt,0)) as pre_authorized_Amt 
     -- ,(ifnull(num_redeem,0)) as num_redeem     

            ,ifnull(channel_type,'UD') channel_type
            ,ifnull(network,'UD') network
-----------VIP---------
            ,case when ifnull(VIP.account_id,-1)>0 then 'VIP' else 'Other' end as IsVIP
            ,ifnull(agent_name,'UD') as agent_name
            ,ifnull(requester_name,'UD') as Zendesk_Requester_name           
            ,ifnull(agent_start_mangaed_date,'1900-01-01') as agent_start_mangaed_date
            ,ifnull(last_contact_date,'1900-01-01') as last_contact_date
           -- ,ifnull(num_VIP_changes,0) as num_VIP_changes
            ,case when extract(year from ifnull(agent_start_mangaed_date,'1900-01-01'))>1900 then DATE_DIFF(ifnull(agent_start_mangaed_date,'1900-01-01'), ftp_date , day) else -1 end as DaysToVIP
--------------------
            ,case when(player_det.locked)=true then 'Locked' else 'Other' end as IsLocked
            ,ifnull(player_det.locked_at,'2099-01-01') as locked_at 
            ,ifnull(player_det.lock_reason,'UD') as lock_reason     
            ,ifnull(player_det.lock_reason_comment,'UD') as lock_reason_comment     
            ,ifnull(player_det.phone_number,'UD') as phone_number  
             ,ifnull(player_det.name,'UD') as name     
            ,ifnull(player_det.email,'UD') as email     
            ,ifnull(player_det.redeem_status,'UD') as redeem_status     
            ,player_det.test_user as test_user     
            ,ifnull(date_of_birth,'1900-01-01') as date_of_birth
             , case when ifnull(date_of_birth,'1900-01-01')='1900-01-01' then -1 else DATE_DIFF( DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY), date_of_birth, YEAR) end as Age
            ,ifnull(player_det.first_name,'UD') as first_name     
            ,ifnull(player_det.last_name,'UD') as last_name     
            ,ifnull(player_det.uuid,'UD') as uuid     
            ,ifnull(player_det.KYC,'UD') as KYC     
            
             ,(ifnull(sc_balance,0)) as  last_sc_balance
             ,(ifnull(last_redeemable_balance,0)) as  last_redeemable_balance
             ,(ifnull(last_unplayed_balance,0)) as  last_unplayed_balance

             ,case when (sus.do_not_send_emails)=TRUE then 0 else 1 end as  Is_Subscribed_Email
             ,case when (sus.do_not_send_pushes)=TRUE then 0 else 1 end as  Is_Subscribed_Push
             ,case when (sus.do_not_send_sms)=TRUE then 0 else 1 end as  Is_Subscribed_SMS
             ,case when (sus.do_not_call)=TRUE then 0 else 1 end as  Is_Subscribed_Calls

             ,(ifnull(mv.max_LT_NGR,0)) as  MaxValue_NGR
             ,(ifnull(mv.max_LT_NP,0)) as  MaxValue_NetPurchase
             ,(ifnull(mv.LT_NGR,0)) as  LT_NGR
             ,(ifnull(mv.LT_net_purchases,0)) as  LT_net_purchases
             ,(ifnull(LT_purchased_num,0)) as  LT_purchased_num
             ,(ifnull(LT_purchased,0)) as  LT_purchased
            ,ifnull(mv.Last_Purchase_date,'1900-01-01') as Last_Purchase_date 
            ,ifnull(mv.Last_Redeem_date,'1900-01-01') as Last_Redeem_date 
            ,ifnull(mv.Last_Active_date,'1900-01-01') as Last_Active_date 
            ,ifnull(mv.Last_Rewards_date,'1900-01-01') as Last_Rewards_date 

            ,case when ftp_date<'2099-01-01' then DATE_DIFF( DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY),ftp_date , day) else 0 end as Days_From_FTP
            ,DATE_DIFF( DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY) , reg_date, day) as Days_From_REG
            ,case when ftp_date<'2099-01-01' then DATE_DIFF(ftp_date,reg_date , day) else 0 end as Days_FTPtoREG

            ,ifnull(value_seg.last_user_segment,'No Segment') as LastValueSegmentName
            ,ifnull(value_seg.last_user_segment_org_number,-999) as LastValueSegmentNumber   
             ,ifnull(value_seg.is_from_model,-999) as IsValueSegmentFromModel
            ,ifnull(value_seg.test_group,'UD') as ValueSegmentTestGroup
     

from RU1
      left join D on D.date=RU1.reward_date and D.account_id=RU1.account_id
     left join VIP on VIP.account_id=RU1.account_id
     left join flag on flag.account_id=RU1.account_id --and date(flagged_from)=(d.date)
     left join MC on MC.account_id=RU1.account_id
     left join player_det on player_det.account_id=RU1.account_id
     left join joinbalance on joinbalance.account_id=RU1.account_id --and joinbalance.ref_date=d.date
     left join Sensai on  Sensai.account_id_SentSensAI=RU1.account_id
      left join players_birth_date birth on birth.account_id=RU1.account_id
      left join MaxValue mv on mv.account_id=RU1.account_id 
      left join sus sus on sus.account_id=RU1.account_id 
      left join `silver-social-games-data.patrianna_view.last_user_segment_v` as value_seg on value_seg.account_id=RU1.account_id 


 -- where 
--  RU1.account_id = 57543884

group by all

having RU1.reward_date>=DATE_SUB(CURRENT_DATE(), INTERVAL 180 DAY)
and D.date>=DATE_SUB(CURRENT_DATE(), INTERVAL 180 DAY)