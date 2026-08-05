with  X as (      select*
                  from
                    
                         (         
                                    SELECT account_id as account_id_red, max(ftp_date) as ftp_date,max(date(reg_date)) as reg_date , max(reg_date) as Reg_DateDime
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
                                                                                   
                                                                 
                                    group by account_id
                                          ,reg_state
                                          ,reg_country
                                          ,unified_channel 
                                          ,adgroup_name
                  )   as det
                  left join  (  select
                                          id,
                                          account_id,
                                          created_at,
                                          amount as ftp_amount
                                          from `transactional_data.payment_payment_orders`
                                          where success
                                          qualify rank() over (partition by account_id order by created_at)=1
                                     ) as FTP   on det.account_id_red=FTP.account_id

)


, d as  
 (
 
       select 
                  d.account_id	
                       , date_diff(d.date,ifnull(ftp_date,'2099-01-01') ,day) as DaysFromFTP   
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

                  , ifnull(acc.Reg_DateDime,'2099-01-01 00:00:00.00') as Reg_DateDime
                  , ifnull(acc.created_at,'2099-01-01 00:00:00.00') as FTP_DateDime     
                  ,max(DATE_DIFF(ifnull(acc.created_at,'2099-01-01 00:00:00.00'), ifnull(Reg_DateDime,'2099-01-01 00:00:00.00'), minute)) Reg2Purcahse_Minutes
      
                    , ifnull(ftp_amount,0) as ftp_amount

                  ,ifnull(adgroup_name,'UD') as AdGroupName

                  , case when ifnull(ftp_date,'2099-01-01')<'2099-01-01' then 1 else 0 end as IsFTP
                  ,d.date
                   ,acc.reg_state
                    ,acc.reg_country
                   ,acc.unified_channel

                  -- ,brand			
                        -- ,country
                  --,count(distinct bonus_type) as numn_BT
                  --- ,bonus_type	
                  --,d.date
                  ,sum(ifnull(profit,0)-ifnull(loss,0)-ifnull(sc_reward_amount,0) ) as NGR
                  ,sum(coalesce(redeemed,0)) as redeemed
                  ,sum(coalesce(purchased,0)) as purchased
                  ,sum(ifnull(purchased,0)-ifnull(redeemed,0)-ifnull(chargeback,0)-ifnull(refunds,0)) as net_purchases

                  ,sum(ifnull(purchased_num,0)) as purchased_num
                  ,sum(ifnull(purchased_attempted,0)) as purchased_attempted
                  ,sum(ifnull(redeemed_num,0)) as redeemed_num
                  ,sum(ifnull(redeem_created,0)) as redeem_created
                  ,sum(ifnull(redeemed_amt_confirmed_locked_pre,0)) as redeemed_amt_confirmed_locked_pre
                  ,sum(ifnull(redeemed_amount_confirmed_on_confirm_date,0)) as redeemed_amount_confirmed_on_confirm_date
                  ,sum(ifnull(redeem_confirmed_amt,0)) as redeem_confirmed_amt
                  ,sum(ifnull(cancelled_redeem,0)) as cancelled_redeem 
                  ,sum(ifnull(spins,0)) as spins
                  ,sum(ifnull(profit,0)) as Bets
                  ,sum(ifnull(loss,0)) as Payout
                  ,sum(ifnull(profit,0))- sum(ifnull(loss,0)) as SC_GGR

                  ,sum(ifnull(spins_gc,0)) as GC_spins
                  ,sum(ifnull(profit_gc,0)) as GC_Bets
                 -- ,sum(ifnull(loss_gc,0)) as GC_Payout
                 -- ,sum(ifnull(profit_gc,0))- sum(ifnull(loss_gc,0)) as GC_GGR

                  ,sum(ifnull(chargeback,0)) as chargeback

                  ,sum(ifnull(sc_reward_amount,0)) as sc_reward_amount
                     ,sum(ifnull(refunds_num,0)) as refunds_num
                  ,sum(ifnull(refunds,0)) as refunds
                  ,count(distinct case when coalesce(purchased,0) > 0 then d.date else NULL end ) as APD_Purchase
                  ,count(distinct case when ifnull(redeem_created,0) > 0 then d.date else NULL end ) as APD_Redeem
                  ,count(distinct case when coalesce(spins,0) > 0 then d.date else NULL end ) as APD_Active
                  ,count(distinct case when coalesce(sc_reward_amount,0) > 0 then d.date else NULL end ) as APD_Rewards



                        FROM  `silver-social-games-data.jackpota_agg.daily_player_revenue_kpis` as d
                          left join x  as acc on acc.account_id_red=d.account_id
                where 
                        d.date between  '2024-01-01' and   DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
                                    
                  group by
                  account_id			
                  --    ,brand			
                  --  ,country			
                  ,d.date
                  ,acc.reg_state
                        ,acc.reg_country
                        ,acc.unified_channel
                        ,date_diff(d.date,ifnull(ftp_date,'2099-01-01') ,day)
                  -- ,bonus_type	
                  ,ifnull(ftp_amount,0)
                  ,ifnull(ftp_date,'2099-01-01')
                  , ifnull(reg_date,'2099-01-01')
                  ,ifnull(acc.Reg_DateDime,'2099-01-01 00:00:00.00')
                  , ifnull(acc.created_at,'2099-01-01 00:00:00.00')
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

, VIP_hist as 
(

select  c.snapshot_date as hist_snapshot_date 
      , c.account_id as hist_account_id
			, case when ifnull(v.account_id,-1)>0 then 1 else 0 end as Is_Currently_VIP
      , ifnull(tag_agent_1,'ud') as hist_tagAgent1
      , ifnull(tag_agent_2,'ud') as hist_tagAgent2
      , ifnull(tag_agent_3,'ud') as hist_tagAgent3
      , ifnull(tag_agent_4,'ud') as hist_tagAgent4
      --, row_number() over (partition by account_id order by snapshot_date desc) as rn 
from silver-social-games-data.dbt_utils.elite_account_tags c
			left join Current_VIP v on c.account_id=v.account_id
where tag_agent_1 is not null

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
				--,max(last_update) as last_contact_date

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
				--	lower(a.email) like '%silver%'
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
  
 
 
, redeem_his as
      (

                  select 
                                        account_id	 as red_account_ID	,	
                                        --ID,
                                        date(created_at) as created_at,
                                         -- status			,
                                        --  uam_status		,			
                                          sum(amount) as red_amt ,
                                          sum(case when status in ('cancelled'  ,  'declined' , 'failed') then amount else 0 end)    as   Cancllend_Amt,
                                          sum(case when status in ('locked'  ,  'confirmed') then amount else 0 end)                 as   locked_confirmed_Amt,
                                          sum(case when status in ('pre_authorized') then amount else 0 end)                 as   pre_authorized_Amt,
                                          count(distinct ID) as num_redeem
                                    from `transactional_data.payment_withdraw_money_requests` c
                                    where  date(created_at) between '2024-01-01' and   DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY) 
                                               -- and account_id=287594267
                                     group by   
                                          account_id	,
                                          date(created_at)
                                         
      ) --as redeem_his on redeem_his.red_account_ID=d.account_id and redeem_his.created_at=d.date
, first_redeem as
      (

                  select 
                                        red_account_ID	 as red_account_ID,	
                                        min(created_at) as FirstDateRedeem,
                                        min(case when locked_confirmed_Amt+pre_authorized_Amt>0 then  created_at else '2099-01-01' end) as FirstDateRedeemPaid,
                                        min(case when Cancllend_Amt>0 then  created_at else '2099-01-01' end) as FirstDateRedeemCancllend

                                    from redeem_his
                                     group by   
                                          red_account_ID	                                         
      ) 


/*
, pur_limit as (


      select      
                  account_id as limit_account_id,
                  threshold as purchase_limit,
                  reason as purchase_limit_reason,
                  date(valid_from) as limit_from_Date,
                  --date(valid_to) as valid_to,

                  date(ifnull(limit_end,'2099-01-01')) as  limit_end_date,
                  case when CURRENT_DATE() between  date(valid_from) and date(ifnull(limit_end,'2099-01-01')) then 1 else 0 end as Is_Pur_Limit_Currently
      from `jackpota_agg.scd_payment_account_purchase_limit`
      where inactive=false
            and valid_from is not null
           -- and ifnull(limit_end,current_date-1)>current_date
      order by account_id

)
*/

,  current_limits AS (

  SELECT
    account_id,
    threshold AS purchase_limit,
    reason AS purchase_limit_reason,
    days,

    DATE(valid_from) AS limit_start_date,
    DATE(IFNULL(limit_end, '2099-01-01')) AS limit_end_date

  FROM `jackpota_agg.scd_payment_account_purchase_limit`

  WHERE inactive = FALSE
         AND valid_from IS NOT NULL

    -- active today
    AND CURRENT_DATE() BETWEEN
        DATE(valid_from)
        AND DATE(IFNULL(limit_end, '2099-01-01'))

),

-- if multiple active limits exist for same player + same days bucket,
-- keep highest/newest
deduped AS (

  SELECT *
  FROM (

    SELECT
      *,

      ROW_NUMBER() OVER (
        PARTITION BY account_id, days
        ORDER BY
          purchase_limit DESC,
          limit_start_date DESC
      ) AS rn

    FROM current_limits

  )

  WHERE rn = 1

)

, resolved_current_purchase_limit as (
SELECT

  account_id,

  -- 1 day
  MAX(CASE WHEN days = '1-Days'
      THEN purchase_limit END) AS limit_1day,

  MAX(CASE WHEN days = '1-Days'
      THEN limit_start_date END) AS limit_1day_start,

  --MAX(CASE WHEN days = '1-Days'      THEN limit_end_date END) AS limit_1day_end,

  -- 1 week
  MAX(CASE WHEN days = '1-Weeks'
      THEN purchase_limit END) AS limit_1week,

  MAX(CASE WHEN days = '1-Weeks'
      THEN limit_start_date END) AS limit_1week_start,

  --MAX(CASE WHEN days = '1-Weeks'      THEN limit_end_date END) AS limit_1week_end,

  -- 4 weeks
  MAX(CASE WHEN days = '4-Weeks'
      THEN purchase_limit END) AS limit_4weeks,

  MAX(CASE WHEN days = '4-Weeks'      THEN limit_start_date END) AS limit_4weeks_start,

  --MAX(CASE WHEN days = '4-Weeks'      THEN limit_end_date END) AS limit_4weeks_end,
        -- overall indication
  CASE
    WHEN COUNT(*) > 0 THEN 1
    ELSE 0
  END AS is_currently_limited,
  /*
  CASE
    WHEN MAX(CASE WHEN days = '1-Days' THEN 1 END) = 1
    THEN 1 ELSE 0
  END AS has_1day_limit,
  CASE
    WHEN MAX(CASE WHEN days = '1-Weeks' THEN 1 END) = 1
    THEN 1 ELSE 0
  END AS has_1week_limit,
  CASE
    WHEN MAX(CASE WHEN days = '4-Weeks' THEN 1 END) = 1
    THEN 1 ELSE 0
  END AS has_4weeks_limit
  */
FROM deduped
GROUP BY 1
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
                                    a.reg_partnerid,
                                    case when b.partner_type is not null then b.partner_type when lower(a.unified_channel) in ('crm','direct','unlabelled','brokem from app') then 'Rest' else 'Organic' end as                                       channel_type
                                   from `dbt_marketing_mart.player_stats_daily` a left join `dbt_mappings.combined_partner_mapping` b on lower(trim(a.reg_partnerid))=lower(trim(b.source_id))
                                ) --as MC on MC.account_id=d.account_id


, player_det as
         (
        select distinct
                 ua.id as account_id
                 ,ua.internal as test_user
                 ,locked_at
                  ,ua.lock_reason_comment
                  ,ua.locked
                  , ua.phone_number
                  ,ua.email
                  --,ua.name
                  ,ua.status as redeem_status
                  ,ua.lock_reason
                  
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


, IsBigWinner as 
 (	
			select   account_ID, min(date) as min_date  
			from
			(
			
						select *  ,SUM(GGR)  OVER (PARTITION BY x.account_id ORDER BY x.date asc
																--ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
															) AS GGR_Cummaltive
					from
						(
								select 
													d.account_id	
													,d.date                    
													,sum(ifnull(profit,0)-ifnull(loss,0)-ifnull(sc_reward_amount,0) ) as NGR
													,sum(coalesce(redeemed,0)) as redeemed
													,sum(coalesce(purchased,0)) as purchased
													,sum(ifnull(purchased,0)-ifnull(redeemed,0)-ifnull(chargeback,0)-ifnull(refunds,0)) as net_purchases
													,sum(ifnull(profit,0)) as Bets
													,sum(ifnull(loss,0)) as Payout
													,sum(ifnull(profit,0))-sum(ifnull(loss,0)) as GGR
										FROM  `silver-social-games-data.jackpota_agg.daily_player_revenue_kpis` as d
										where 
																d.date between  '2024-06-01' and   DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
										group by
													d.account_id	
													,d.date        
						) as x	
			) as x
			where GGR_Cummaltive <-40000
			group by account_ID
 ) 

 , Contacts as 
(
			select 
				tab.account_id
                        ,date(created_at) as ticket_created_at
				,count(distinct ticket_id) as num_tickets
                        ,count(distinct case when lower(VIP.agent_name) like '%alon%' then ticket_id else NULL end) as num_tickets_OrigAlon
                        ,count(distinct case when lower(VIP.agent_name) like '%daniel%' then ticket_id else NULL end) as num_tickets_OrigDaniel
                        ,count(distinct case when lower(VIP.agent_name) like '%gabriel%' then ticket_id else NULL end) as num_tickets_OrigGabriel
                        ,count(distinct case when lower(VIP.agent_name) like '%coral%' then ticket_id else NULL end) as num_tickets_OrigCoral
                        
                        ,count(distinct case when lower(tab.agent_name) like '%alon%' then ticket_id else NULL end) as num_tickets_ActualAlon
                        ,count(distinct case when lower(tab.agent_name) like '%daniel%' then ticket_id else NULL end) as num_tickets_ActualDaniel
                        ,count(distinct case when lower(tab.agent_name) like '%gabriel%' then ticket_id else NULL end) as num_tickets_ActualGabriel
                        ,count(distinct case when lower(tab.agent_name) like '%coral%' then ticket_id else NULL end) as num_tickets_ActualCoral
			from
				(
				select
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
					lower(a.email) like '%silver%'
					and ua.id  is not null
                             -- and ua.id=150041967
				) as tab  left join VIP on VIP.account_id=tab.account_id
			group by 
				tab.account_id
                        ,date(created_at)
			
	) 
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



, sus as
(
select distinct
      a.id as account_id,
      b.do_not_send_emails,
      b.do_not_send_pushes,
      b.do_not_send_sms,
      b.do_not_call
      
from `transactional_data.uam_accounts` a join `transactional_data.uam_account_preferences` b on a.id=b.id
)

/*
,DailySegment as 
(
        SELECT distinct account_id,
                snapshot_date,
                user_segment, 
               rank() over (partition by account_id order by snapshot_date asc) as rn_segment
        FROM `silver-social-games-data.ml_platform.user_segments`
)
*/

, sign_up_method as
(
      SELECT distinct account_id,
      sign_up_method
FROM
  `silver-social-games-data.jackpota_agg.tbl_attribution_cube` 
)


, base as (select
account_id,
coalesce(min(id_state),min(doc_state)) as doc_state
from `transactional_data.uam_kyc_verification_requests` a group by 1 ),
base_b as(
select
account_id,
b.state_name as state
from base a left join `dbt_mappings.states_mapping` b on lower(doc_state)=lower(b.state_code)
)
,logins as (
SELECT distinct
  `id`,
  -- reg_state as CurrentUserRegState,
  `sign_up_state`,
  `last_sign_in_state`,
  `last_sign_in_city`,
  --`last_sign_in_country`,
 -- `sign_up_city`,
  --`sign_up_state`,
 -- `sign_up_ip`,
 -- last_sign_in
FROM
  `silver-social-games-data.transactional_data.uam_account_auth_info` as x
  left join (
      SELECT distinct account_id, reg_state
      FROM `silver-social-games-data.dbt_marketing_mart.player_stats_daily` as a
  ) as a on x.id=a.account_id
)

, States as
(select 
distinct
a.account_id,
lower(reg_state) as reg_state,
lower(trim(ifnull(b.state,'UNKOWN'))) as state_KYC,
lower(ifnull(l.last_sign_in_state,'UNKOWN')) as Last_Sign_State,
lower(ifnull(l.last_sign_in_city,'UNKOWN')) as Last_Sign_City

from
            `dbt_marketing_mart.player_stats_daily` a 
            left join base_b b using(account_id)
            left join logins l on l.id=a.account_id
)
    






 /*---------------------------------------------------------------------*/
/*---------------------------------------------------------------------*/


 /*---------------------------------------------------------------------*/
/*---------------------------------------------------------------------*/



 /*------------------------PREDICATION 180 DAYS-----------------------------------------------*/
, dates_pred as (
      select distinct d.date , account_id , IsFTP , DaysFromFTP , ftp_date
      from d as d
      where d.date>='2025-11-29'
)
,DailySegment_FromPred as 
(
        SELECT distinct d.account_id,
                  d.date,
                snapshot_date,
                user_segment, 
                IsFTP,
                d.ftp_date,
                DaysFromFTP,
               rank() over (partition by d.account_id , d.date order by snapshot_date desc) as rn_segment
        FROM  dates_pred d  inner join  `silver-social-games-data.ml_platform.user_segments` seg      
                        on d.date>=seg.snapshot_date and seg.account_id=CAST(d.account_id AS STRING) 
             
)


,DailySegment_Final as 
(
select date
      ,snapshot_date 
      , account_id 
      ,user_segment
     -- ,DaysFromFTP
      --,ftp_date
from DailySegment_FromPred
where rn_segment=1 
      and DaysFromFTP between  1 and 180
group by date,snapshot_date ,account_id ,user_segment --,DaysFromFTP,ftp_date
             
)

 /*------------------------>180 FIRST DAYS-----------------------------------------------*/

/*
 ,LT_calc as 
  (
            select 
                  d.account_id	
                  ,d.date 
                  ,DaysFromFTP
                  ,ftp_date
                  ,sum(ifnull(NGR,0)) as NGR
                  ,sum(coalesce(purchased,0)) as purchased
                  ,sum(ifnull(purchased_num,0)) as purchased_num
                  ,sum(ifnull(purchased,0)-ifnull(redeemed_amt_confirmed_locked_pre,0)-ifnull(chargeback,0)-ifnull(refunds,0)) as net_purchases
                  ,sum(ifnull(redeem_created,0)) as redeem_created
                  ,sum(ifnull(spins,0)) as spins
                  ,sum(ifnull(sc_reward_amount,0)) as sc_reward_amount

            FROM  --`silver-social-games-data.jackpota_agg.daily_player_revenue_kpis` 
                        d as d
            
             group by
                   d.account_id	
                  ,d.date
                   ,DaysFromFTP
                  ,ftp_date
 ) 
*/
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
      ,SUM(purchased_num)
                        OVER (
                  PARTITION BY LT_calc.account_id	
                  ORDER BY LT_calc.date asc
                  ) AS purchased_num_Cummaltive      
from d as LT_calc      
    left join redeem_his on redeem_his.red_account_ID=LT_calc.account_id and redeem_his.created_at=LT_calc.date 

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
          ,sum(ifnull(refunds,0)) as LT_refunds
          ,sum(ifnull(chargeback,0)) as LT_chargeback
          ,sum(sc_reward_amount) as LT_reward_amount
          ,sum(Bets) as LT_Bets
          ,sum(SC_GGR) as LT_GGR
          ,sum(ifnull(purchased,0)-  (ifnull(red_amt,0)-ifnull(Cancllend_Amt,0))
            -ifnull(chargeback,0)-ifnull(refunds,0)) as LT_net_purchases_ByReq
          ,sum(case when coalesce(purchased,0) > 0 then 1 else 0 end ) as LT_PurchaseDays
          ,max( case when coalesce(purchased,0) > 0 then date else '1900-01-01' end ) as Last_Purchase_date
          ,max( case when ifnull(redeem_created,0) > 0 then date else '1900-01-01' end ) as  Last_Redeem_date
          ,max( case when coalesce(spins,0) > 0 then date else '1900-01-01' end ) as  Last_Active_date
          ,max( case when coalesce(sc_reward_amount,0) > 0 then date else '1900-01-01' end ) as  Last_Rewards_date
  from LT
  group by 
      account_id
)

/*
,DAA as (
select * ,SUM(NGR)
                        OVER (
                  PARTITION BY d.account_id	
                  ORDER BY d.date asc
                  ) AS NGR_Cummaltive
	,SUM(net_purchases)
                        OVER (
                  PARTITION BY d.account_id	
                  ORDER BY d.date asc
                  ) AS net_purchases_Cummaltive

               
from d
)
*/
,MaxValueToDate as 
(
  select  *,
            MAX(NGR_Cummaltive) OVER (
            PARTITION BY account_id
            ORDER BY date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS max_NGR_To_Date,
            MAX(net_purchases_Cummaltive) OVER (
            PARTITION BY account_id
            ORDER BY date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS max_NP_To_Date 
  from LT-- DAA
  --where DaysFromFTP >180 

)

 /*------------------------First Day-----------------------------------------------*/
, DailySegment as
(
select 
       distinct
       d.account_id
       ,d.date
       ,d.DaysFromFTP
        ,case when d.DaysFromFTP=0 then 'First Day' 
              when ifnull(ls.user_segment,'-1')<>'-1' and d.DaysFromFTP between 1 and 180 and extract(year from ftp_date)<2099 then 
                  case when ls.user_segment='0' then 'Negative'
                  when ls.user_segment='1' then 'Low'
                  when ls.user_segment='2' then 'Low Mid'
                  when ls.user_segment='3' then 'Mid'
                  when ls.user_segment='4' then 'HV Potential'
                  when ls.user_segment='5' then 'HV'
                  when ls.user_segment='6' then 'Elite'        
                  end
             when (ifnull(ls.user_segment,'-1')='-1' or d.DaysFromFTP>180) and extract(year from ftp_date)<2099 then 
                        case when max_NP_To_Date<= 0 then 'Negative'
                              when max_NP_To_Date<= 9.99  then 'Low'
                              when max_NP_To_Date<= 29.98 then 'Low Mid'
                              when max_NP_To_Date<= 297.35 then 'Mid'
                              when max_NP_To_Date<= 654.3 then 'HV Potential'
                              when max_NP_To_Date<= 3524.2 then 'HV'
                              when max_NP_To_Date > 3524.2 then 'Elite'
                              else 'UD' end 
            else 'UD' end as Daily_User_segment 
         ,case when ifnull(ls.user_segment,'-1')<>'-1' and d.DaysFromFTP between 1 and 180 then 1 else 0 end as IsFromModel
from MaxValueToDate as d
      left join DailySegment_Final as ls on ls.account_id=d.account_id and ls.date=d.date
where 1=1
      and DaysFromFTP>=0
)    




/*---------------------------------------------------------------------*/
/*---------------------------------------------------------------------*/
/*---------------------------------------------------------------------*/
/*---------------------------------------------------------------------*/







-- Simple daily player table: churn + reactivation flags (FTP-based timeline)
-- Days are calculated ONLY from player's FTP (first purchase date).
-- Definitions:
-- Is Churn = (days since last purchase) >= 10
-- Is Churn Today = (days since last purchase) = 10
-- Is Reactivated Today = purchased today AND gap from previous purchase >= 10


,params AS (
  SELECT
    DATE '2024-06-01' AS start_date,
    DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY) AS end_date,
    20 AS churn_period_days
),

/* Successful purchases */
purchases AS (
  SELECT
    p.account_id,
    DATE(p.at) AS purchase_date
  FROM `transactional_data.payment_payment_orders` p
  WHERE p.success = TRUE
    AND DATE(p.at) BETWEEN (SELECT start_date FROM params)
                       AND (SELECT end_date FROM params)
),

/* FTP per player */
FTP AS (
  SELECT
    account_id,
    MIN(purchase_date) AS FTP_date
  FROM purchases
  GROUP BY 1
),

/* One row per player per purchase-day */
purchases_daily AS (
  SELECT
    account_id,
    purchase_date,
    TRUE AS purchased_today
  FROM purchases
  GROUP BY 1,2
),

/* Date spine from FTP only */
date_spine AS (
  SELECT
    f.account_id,
    d AS date
  FROM FTP f
  CROSS JOIN UNNEST(
    GENERATE_DATE_ARRAY(
      GREATEST(f.FTP_date, (SELECT start_date FROM params)),
      (SELECT end_date FROM params)
    )
  ) AS d
),

/* Daily player state */
player_day AS (
  SELECT
    ds.account_id,
    ds.date,
    f.FTP_date,

    pd.purchased_today,

    LAST_VALUE(pd.purchase_date IGNORE NULLS) OVER (
      PARTITION BY ds.account_id
      ORDER BY ds.date
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS last_purchase_date,

    LAST_VALUE(pd.purchase_date IGNORE NULLS) OVER (
      PARTITION BY ds.account_id
      ORDER BY ds.date
      ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
    ) AS last_purchase_date_prev

  FROM date_spine ds
  JOIN FTP f
    ON f.account_id = ds.account_id
  LEFT JOIN purchases_daily pd
    ON pd.account_id = ds.account_id
   AND pd.purchase_date = ds.date
)


, Churn_Times as
(

SELECT
  account_id ,                             -------------------- Topaz you can remove from final select
  date,                                           -----------------------left Join on date_spine.date and Account_ID
  --FTP_date,                                        -------------------- Topaz you can remove from final select
  --DATE_DIFF(date, FTP_date, DAY) AS days_since_FTP,-------------------- Topaz you can remove from final select

 -- last_purchase_date,
  DATE_DIFF(date, last_purchase_date, DAY) AS days_since_last_purchase,

 -- (SELECT churn_period_days FROM params) AS churn_period_days, -------------------- Topaz you can remove from final select

  /* Churn state (>= 10 days since last purchase) */
  (last_purchase_date IS NOT NULL
   AND DATE_DIFF(date, last_purchase_date, DAY) >= (SELECT churn_period_days FROM params)
  ) AS is_churn,

  /* Churn event day (exactly day 10) */
  (last_purchase_date IS NOT NULL
   AND DATE_DIFF(date, last_purchase_date, DAY) = (SELECT churn_period_days FROM params)
  ) AS is_churn_today,

  /* Reactivation event day */
  (IFNULL(purchased_today, FALSE)
   AND last_purchase_date_prev IS NOT NULL
   AND DATE_DIFF(date, last_purchase_date_prev, DAY) >= (SELECT churn_period_days FROM params)
  ) AS is_reactivated_today

FROM player_day
--where account_id = 73459538
)

/*---------------------------------------------------------------------*/
/*---------------------------------------------------------------------*/
/*---------------------------------------------------------------------*/
/*---------------------------------------------------------------------*/
/*---------------------------------------------------------------------*/
/*---------------------------------------------------------------------*/

, HighRisk as (
select distinct id
from `silver-social-games-data.temp.Topaz_HighRiskListAccounts` 

)


select  d.* 
			 /*
	      IFNULL(games.SC_Bets,0) as SC_Bets,
            IFNULL(games.SC_Payout,0) as SC_Payout,
            IFNULL(games.SC_GGR,0) as SC_GGR,
            IFNULL(games.SC_Rounds,0) as SC_Rounds,
            IFNULL(games.GC_Bets,0) as GC_Bets,
            IFNULL(games.GC_Payout,0) as GC_Payout,
            IFNULL(games.GC_GGR,0) as GC_GGR,
            IFNULL(games.GC_Rounds,0) as GC_Rounds,
            IFNULL(games.Bets_SLOTS_SC,0) as Bets_SLOTS_SC,
            IFNULL(games.Bets_LIVE_SC,0) as Bets_LIVE_SC,
            IFNULL(games.Bets_JACKPOT_SC,0) as Bets_JACKPOT_SC,
            IFNULL(games.Bets_OTHER_SC,0) as Bets_OTHER_SC,
            IFNULL(games.Rounds_SLOTS_SC,0) as Rounds_SLOTS_SC,
            IFNULL(games.Rounds_LIVE_SC,0) as Rounds_LIVE_SC,
            IFNULL(games.Rounds_JACKPOT_SC,0) as Rounds_JACKPOT_SC,
            IFNULL(games.Rounds_OTHER_SC,0) as Rounds_OTHER_SC,
            IFNULL(games.NumGames_SC,0) as NumGames_SC,
            IFNULL(games.NumGames_GC,0) as NumGames_GC,
            IFNULL(games.NumGames_SLOTS_SC,0) as NumGames_SLOTS_SC,
            IFNULL(games.NumGames_LIVE_SC,0) as NumGames_LIVE_SC,
            IFNULL(games.NumGames_OTHER_SC,0) as NumGames_OTHER_SC

             
            ,IFNULL(games.Rounds_Roulette_Game_SC,0) as Rounds_Roulette_Game_SC
            ,IFNULL(games.Rounds_Plinko_Game_SC,0) as Rounds_Plinko_Game_SC
            ,IFNULL(games.Rounds_BJ_Game_SC,0) as Rounds_BJ_Game_SC
            ,IFNULL(games.Rounds_Roulette_Live_Game_SC,0) as Rounds_Roulette_Live_Game_SC
            ,IFNULL(games.Rounds_Plinko_Live_Game_SC,0) as Rounds_Plinko_Live_Game_SC
            ,IFNULL(games.Rounds_BJ_Live_Game_SC,0) as Rounds_BJ_Live_Game_SC
            ,IFNULL(games.Bets_Roulette_Game_SC,0) as Bets_Roulette_Game_SC
            ,IFNULL(games.Bets_Plinko_Game_SC,0) as Bets_Plinko_Game_SC
            ,IFNULL(games.Bets_BJ_Game_SC,0) as Bets_BJ_Game_SC
            ,IFNULL(games.Bets_Roulette_Live_Game_SC,0) as Bets_Roulette_Live_Game_SC
            ,IFNULL(games.Bets_Plinko_Live_Game_SC,0) as Bets_Plinko_Live_Game_SC
            ,IFNULL(games.Bets_BJ_Live_Game_SC,0) as Bets_BJ_Live_Game_SC


            ,IFNULL(games.SC_Bets_FS,0) as SC_Bets_FS
            ,IFNULL(games. SC_Payout_FS,0) as  SC_Payout_FS
            ,IFNULL(games.SC_GGR_FS,0) as SC_GGR_FS
            ,IFNULL(games.SC_Rounds_FS,0) as SC_Rounds_FS          
*/

      ,ifnull(purchased,0)-  (ifnull(red_amt,0)-ifnull(Cancllend_Amt,0))
            -ifnull(chargeback,0)-ifnull(refunds,0) as net_purchases_ByReq



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


      ,(ifnull(red_amt,0)) as red_amt 
      ,(ifnull(Cancllend_Amt,0)) as Cancllend_Amt	
      ,ifnull(red_amt,0)-ifnull(Cancllend_Amt,0) as RedeemReq_Minus_Cancled
      ,(ifnull(locked_confirmed_Amt,0)) as locked_confirmed_Amt	
      ,(ifnull(pre_authorized_Amt,0)) as pre_authorized_Amt	
      ,(ifnull(num_redeem,0)) as num_redeem	


            ,ifnull(channel_type,'UD') channel_type
            ,ifnull(network,'UD') network
            ,ifnull(mc.reg_partnerid,'UD') Reg_Partner_id

            ,case when ifnull(VIP.account_id,-1)>0 then 'VIP' else 'Other' end as IsVIP
            ,ifnull(agent_name,'UD') as agent_name
            ,ifnull(requester_name,'UD') as Zendesk_Requester_name           
            ,ifnull(agent_start_mangaed_date,'1900-01-01') as agent_start_mangaed_date
            ,ifnull(last_contact_date,'1900-01-01') as last_contact_date
           -- ,ifnull(num_VIP_changes,0) as num_VIP_changes
            ,case when extract(year from ifnull(agent_start_mangaed_date,'1900-01-01'))>1900 then DATE_DIFF(ifnull(agent_start_mangaed_date,'1900-01-01'), ftp_date , day) else -1 end as DaysToVIP

             ,ifnull(player_first_contact,'1900-01-01') as player_first_contact
             ,ifnull(player_last_contact,'1900-01-01') as player_last_contact
            ,case when ifnull(vh.hist_account_id,-1)>0 then 1 else 0 end as IS_VIP_THIS_DAY
            ,ifnull(hist_tagAgent1,'UD') as THIS_DAY_VIP_AGENT      



            ,ifnull(IsBigWinner.min_date,'1900-01-01') as BigWinner_min_date_Winning
            ,case when ifnull(VIP.account_id,-1)>0 then case when extract(year from ifnull(IsBigWinner.min_date,'1900-01-01'))>1900 then 
                  case when  ifnull(agent_start_mangaed_date,'1900-01-01')>= min_date then
                              case when DATE_DIFF(min_date, ifnull(agent_start_mangaed_date,'1900-01-01'), day) <=2 then 'Elite Promoted Due To Win 3D'
                                   when DATE_DIFF(min_date, ifnull(agent_start_mangaed_date,'1900-01-01'), day) <=6 then 'Elite Promoted Due To Win 7D'
                              else 'Became VIP >7 Days After Win' end
                  else 'Logic Elite' end
             else 'Logic Elite' end 
             else 'Not Elite Player' end as Is_BigWinner_VIP
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
             /*
             ,(ifnull(num_tickets,0)) as  num_tickets
             ,(ifnull(num_tickets_OrigDaniel,0)) as  num_tickets_OrigDaniel
             ,(ifnull(num_tickets_OrigAlon,0)) as  num_tickets_OrigAlon
             ,(ifnull(num_tickets_OrigGabriel,0)) as  num_tickets_OrigGabriel
             ,(ifnull(num_tickets_OrigCoral,0)) as  num_tickets_OrigCoral
             ,(ifnull(num_tickets_ActualDaniel,0)) as  num_tickets_ActualDaniel
             ,(ifnull(num_tickets_ActualAlon,0)) as  num_tickets_ActualAlon
             ,(ifnull(num_tickets_ActualGabriel,0)) as  num_tickets_ActualGabriel
             ,(ifnull(num_tickets_ActualCoral,0)) as  num_tickets_ActualCoral
              */
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
            ,(ifnull(mv.LT_refunds,0)) as  LT_refunds
             ,(ifnull(mv.LT_chargeback,0)) as  LT_chargeback
             ,(ifnull(mv.LT_reward_amount,0)) as  LT_reward_amount
             ,(ifnull(mv.LT_Bets,0)) as  LT_Bets
             ,(ifnull(mv.LT_GGR,0)) as  LT_GGR
             ,(ifnull(mv.LT_net_purchases_ByReq,0)) as  LT_net_purchases_ByReq


            ,ifnull(mv.Last_Purchase_date,'1900-01-01') as Last_Purchase_date 
            ,ifnull(mv.Last_Redeem_date,'1900-01-01') as Last_Redeem_date 
            ,ifnull(mv.Last_Active_date,'1900-01-01') as Last_Active_date 
            ,ifnull(mv.Last_Rewards_date,'1900-01-01') as Last_Rewards_date 


            ,ifnull(fr.FirstDateRedeem,'1900-01-01') as FirstDateRedeem 
            ,ifnull(fr.FirstDateRedeemPaid,'1900-01-01') as FirstDateRedeemPaid 
            ,ifnull(fr.FirstDateRedeemCancllend,'1900-01-01') as FirstDateRedeemCancllend 

            ,case when ifnull(pur_limit.account_id,-1)>0 then 1 else 0 end as Is_Currntly_Have_Purchase_Limit
            --,(ifnull(purchase_limit_reason,'UD')) as  current_purchase_limit_reason
            --,(ifnull(has_1day_limit,0)) as  has_1day_limit
           -- ,(ifnull(has_1week_limit,0)) as  has_1week_limit
            --,(ifnull(has_4weeks_limit,0)) as  has_4weeks_limit
            ,(ifnull(limit_1day,-1)) as  limit_1day
            ,ifnull(limit_1day_start,'2099-01-01') limit_1day_start
           -- ,ifnull(limit_1day_end,'2099-01-01') limit_1day_end
             ,(ifnull(limit_1week,-1)) as  limit_1week
            ,ifnull(limit_1week_start,'2099-01-01') limit_1week_start
            --,ifnull(limit_1week_end,'2099-01-01') limit_1week_end
             ,(ifnull(limit_4weeks,-1)) as  limit_4weeks
            ,ifnull(limit_4weeks_start,'2099-01-01') limit_4weeks_start
           -- ,ifnull(limit_4weeks_end,'2099-01-01') limit_4weeks_end
              

            ,case when ftp_date<'2099-01-01' then DATE_DIFF( DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY),ftp_date , day) else 0 end as Days_From_FTP
            ,DATE_DIFF( DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY) , reg_date, day) as Days_From_REG
            ,case when ftp_date<'2099-01-01' then DATE_DIFF(ftp_date,reg_date , day) else 0 end as Days_FTPtoREG

            ,ifnull(value_seg.last_user_segment,'No Segment') as LastValueSegmentName
            ,ifnull(value_seg.last_user_segment_org_number,-999) as LastValueSegmentNumber  

            ,ifnull(value_seg.last_orig_user_segment,'No Segment') as last_orig_user_segment
            ,ifnull(value_seg.last_orig_user_segment_org_number,-999) as last_orig_user_segment_org_number 

             ,ifnull(value_seg.is_from_model,-999) as IsValueSegmentFromModel
            ,ifnull(value_seg.test_group,'UD') as ValueSegmentTestGroup

            ,lower(trim(ifnull(state_KYC,'UNKOWN'))) as  KYC_State
            ,lower(ifnull(Last_Sign_State,'UNKOWN')) as Last_Sign_State
            --,lower(ifnull(Last_Sign_City,'UNKOWN')) as Last_Sign_City

            --,case when ifnull(exc.account_id,-1)=-1 then 'ok'  else 'excluded' end IsExcluded

            --,ifnull(CAST(ds.user_segment AS INT64),-999) as DailyFTPValueSegment 
            --,ifnull(ds.rn_segment,-1) as DailyValueSegmentRN

            
            ,ifnull(ds.Daily_User_segment,'No Segment') as Daily_User_Value_Segment
             ,ifnull(ds.IsFromModel,-999) as IsDailyValueSegmentFromModel
             ,case when ifnull(hr.id,-1)>0 then 'High Risk' else 'OK' end as IsHighRiskPlayer


             ,ifnull(days_since_last_purchase,-999) as days_since_last_purchase
             ,case when is_churn = TRUE then 1 else 0 end as is_churn
             ,case when is_churn_today = TRUE then 1 else 0 end as is_churn_today
             ,case when is_reactivated_today = TRUE then 1 else 0 end as is_reactivated_today

            ,ifnull(sign_method.sign_up_method,'UD') as sign_up_method
            ,SUM(d.purchased)
                        OVER (
                  PARTITION BY d.account_id	
                  ORDER BY d.date asc
                  ) AS purchased_Cummaltive
                        
            ,SUM(d.purchased_num)
                        OVER (
                  PARTITION BY d.account_id	
                  ORDER BY d.date asc
                  ) AS purchased_num_Cummaltive


from d
     --left join games on games.account_id=d.account_id and games.at=d.date
     left join redeem_his on redeem_his.red_account_ID=d.account_id and redeem_his.created_at=d.date and  d.date>='2025-01-01'
     left join VIP on VIP.account_id=d.account_id
     left join flag on flag.account_id=d.account_id --and date(flagged_from)=(d.date)
     left join MC on MC.account_id=d.account_id
     left join player_det on player_det.account_id=d.account_id
     left join joinbalance on joinbalance.account_id=d.account_id --and joinbalance.ref_date=d.date
     left join IsBigWinner on IsBigWinner.account_id=d.account_id 
     --left join Contacts on Contacts.account_id=d.account_id and Contacts.ticket_created_at=d.date
     left join Sensai on  Sensai.account_id_SentSensAI=d.account_id
      left join players_birth_date birth on birth.account_id=d.account_id
      left join MaxValue mv on mv.account_id=d.account_id
      left join sus sus on sus.account_id=d.account_id
      left join `silver-social-games-data.patrianna_view.last_user_segment_v` as value_seg on value_seg.account_id=d.account_id
     -- left join  DailySegment ds on ds.account_id=CAST(d.account_id AS STRING) and d.date=ds.snapshot_date
     -- left join `silver-social-games-data.patrianna_view.excluded_players` exc on exc.account_id=d.account_id
      left join sign_up_method sign_method on sign_method.account_id=d.account_id
      left join States state on state.account_id=d.account_id
      left join  DailySegment ds on ds.account_id=d.account_id and d.date=ds.date
      left join HighRisk hr on hr.id=d.account_id
      left join Churn_Times as churn on churn.account_id=d.account_id and d.date=churn.date
      left join VIP_hist vh on vh.hist_account_id=d.account_id and vh.hist_snapshot_date=d.date


      left join first_redeem as fr on fr.red_account_ID=d.account_id
      left join resolved_current_purchase_limit as pur_limit on pur_limit.account_id=d.account_id



where 
      d.date>='2025-01-01'
