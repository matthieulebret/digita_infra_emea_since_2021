import pandas as pd
import os
import json
import itertools
import plotly.express as px
import plotly.io as pio
import streamlit as st
from ast import literal_eval
import numpy as np
import openpyxl

from kmodes.kmodes import KModes

pio.renderers.default = 'iframe'

st.set_page_config(layout = 'wide')


st.title('Project finance Europe - market analysis')

col1,col2,col3 = st.columns(3)
with col1:
    st.image('https://images.unsplash.com/photo-1466611653911-95081537e5b7?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTJ8fHNvbGFyJTIwZmFybXxlbnwwfHwwfHx8MA%3D%3D&auto=format&fit=crop&w=500&q=60')
with col2:
    st.image('https://media.istockphoto.com/id/1368036451/photo/fiber-glass-algorithm.webp?b=1&s=170667a&w=0&k=20&c=dBg0QgYMoH8oGTWT50JwZwMdWDD8SUavAP4pdMPKDpI=')
with col3:
    st.image('https://plus.unsplash.com/premium_photo-1682320426935-f0614a9a6517?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTN8fGJyaWRnZXxlbnwwfHwwfHx8MA%3D%3D&auto=format&fit=crop&w=500&q=60')

@st.cache_data
def get_data():
    # path = 'C:/Users/matth/OneDrive/Asus old pc/Documents/Inframation_Europe_Deals since 2021/'

    bigdf = pd.read_excel('deals_insto_europe.xlsx')
    bigdf['lendersFundingValues'] = bigdf['lendersFundingValues'].apply(literal_eval)

    uniqueLenders = pd.read_excel('uniquelenders_classified_for_upload.xlsx')

    lenderdf = pd.DataFrame(bigdf.pop('lendersFundingValues').explode())
    lenderdf = pd.concat([lenderdf, lenderdf['lendersFundingValues'].apply(pd.Series)], axis=1)
    lenderdf = bigdf.join(lenderdf)

    countriesregions = pd.read_excel('uniquecountries.xlsx')

    lenderdf = lenderdf.merge(uniqueLenders,left_on='name',right_on='Name')

    instolist = lenderdf[lenderdf['Bank / Insto']=='Insto']['name'].unique().tolist()

    def WhichCat(bank, insto):
        if bank > 0 and insto > 0:
            return 'Mixed'
        elif insto > 0:
            return 'Insto only'
        else:
            return 'Bank only'

    dealcat = pd.pivot_table(lenderdf[lenderdf['valueEUR'] > 0], values='valueEUR', index='Deal name',
                             columns='Bank / Insto', aggfunc='sum')

    dealcat['Deal Category'] = dealcat.apply(lambda x: WhichCat(x['Bank'], x['Insto']), axis=1)
    dealcat.reset_index(inplace=True)

    lenderdf = lenderdf.merge(dealcat, how='left', on='Deal name')
    lenderdf = lenderdf[lenderdf['summary.debtsizeEUR']>0]

    allocationdf = pd.pivot_table(lenderdf, values='valueEUR', index=['dominantSector', 'Bank / Insto'], aggfunc='sum')
    allocationdf.reset_index(inplace=True)
    allocationdf['Percent'] = 100 * allocationdf['valueEUR'] / allocationdf.groupby('Bank / Insto')['valueEUR'].transform('sum')

    instodeals = lenderdf[lenderdf['Bank / Insto'] == 'Insto']

    marketsunburstvol = pd.pivot_table(lenderdf, values='valueEUR',
                                    index=['Deal Category', 'dominantSector', 'dominantCountry', 'Bank / Insto',
                                           'name'], aggfunc='sum')
    marketsunburstvol.reset_index(inplace=True)


    return bigdf,uniqueLenders,lenderdf,countriesregions,allocationdf,instodeals,instolist, marketsunburstvol

bigdf,uniquelenders,lenderdf,countriesregions,allocationdf,instodeals,instolist, marketsunburstvol = get_data()


tab1,tab2,tab3,tab4 = st.tabs(['General market stats','Deal comparison: bank vs insto','Market participants','Segmentation'])

with tab1:

    df = pd.pivot_table(lenderdf,values='valueEUR',index=['Bank / Insto'],aggfunc='sum')
    df['Pct']=df['valueEUR']*100/df['valueEUR'].sum()
    df.reset_index(inplace=True)

    instodealnb = instodeals['Deal name'].unique().tolist()

    nbinstodeals = len(instodealnb)
    nbdeals = len(lenderdf['Deal name'].unique().tolist())

    st.header('General statistics on the market')

    col1,col2,col3,col4 = st.columns(4)
    with col1:
        st.metric('Total market size bn EUR','{:,.2f}'.format(df['valueEUR'].sum()/1000))
    with col2:
        st.metric('Institutional share of market','{:,.2f}'.format(float(df[df['Bank / Insto']=='Insto']['Pct'])))
    with col3:
        st.metric('Total Insto market size bn EUR','{:,.2f}'.format(df[df['Bank / Insto']=='Insto']['valueEUR'].sum()/1000))
    with col4:
        st.metric('Number of deals with instos / total deals','{:,}'.format(nbinstodeals)+' / '+'{:,}'.format(nbdeals))



    bankonly = len(lenderdf[lenderdf['Deal Category']=='Bank only']['Deal name'].unique().tolist())
    instoonly = len(lenderdf[lenderdf['Deal Category']=='Insto only']['Deal name'].unique().tolist())
    mixed = len(lenderdf[lenderdf['Deal Category']=='Mixed']['Deal name'].unique().tolist())

    df = pd.pivot_table(lenderdf,values='valueEUR',index='Deal Category',aggfunc='sum')
    df['Deal number']=[bankonly,instoonly,mixed]
    df['Average deal size mEUR']= df['valueEUR']/df['Deal number']

    df.reset_index(inplace=True)

    col1,col2 = st.columns(2)

    with col1:
        st.header('Market split - Banks, Instos, Mixed deals (volume)')

        st.info('Half of the market by volume involves instos')
        fig = px.sunburst(marketsunburstvol,path=['Deal Category','dominantSector','dominantCountry'],values='valueEUR')
        st.write(fig)
    with col2:
        st.header('Market split - Banks, Instos, Mixed deals (deal count)')

        st.info('Smaller deals are bank only, while large deals involve a higher proportion of instos')
        fig = px.bar(df,x=['Deal number','Average deal size mEUR'],y='Deal Category',barmode='group',labels={'x':'Average deal size mEUR / Deal count','y':'Deal Category'})
        st.write(fig)

        with st.expander('See data'):
            df


    col1,col2,col3 = st.columns(3)

    with col1:
        st.subheader('Banks vs Insto by volume')
        st.info('The size of the bank market is 5x larger than that of the insto market, in PF loans.')
        # fig = px.line_polar(allocationdf,r='valueEUR',theta='dominantSector',color='Insto investor')
        # st.write(fig)

        fig = px.bar(allocationdf,x='valueEUR',y='dominantSector',color='Bank / Insto')
        fig.update_layout(yaxis={'categoryorder':'total ascending'})
        st.write(fig)

    with col2:
        st.subheader('Banks vs Insto by percentage allocation')
        st.info('Institutional investors allocate more to renewables and transport, less to telecommunications than banks.')

        fig = px.line_polar(allocationdf,r='Percent',theta='dominantSector',color='Bank / Insto')
        st.write(fig)

    with col3:
        st.subheader('Average ticket size bank vs insto')
        st.info('Institutional investors tend to invest in larger tickets vs banks')
        alldeals = pd.pivot_table(lenderdf[lenderdf['valueEUR']>0],index='dominantSector',values='valueEUR',columns='Bank / Insto',aggfunc='mean')

        fig = px.bar(alldeals,x=['Bank','Insto'],barmode='group')
        fig.update_layout(yaxis={'categoryorder':'total ascending'})
        st.write(fig)

with tab2:
    st.header('What do deals with instos look like vs deals without instos?')




    col1,col2 = st.columns(2)

    with col1:

        st.subheader('Total invested on bank only deals')

        df = pd.pivot_table(lenderdf[lenderdf['Deal Category'] == 'Bank only'], index='dominantSector', values='valueEUR',aggfunc='sum')
        fig = px.bar(df)
        fig.update_layout(xaxis={'categoryorder':'total descending'})
        st.write(fig)

    with col2:

        st.subheader('Average ticket size on bank only deals')

        df = pd.pivot_table(lenderdf[lenderdf['Deal Category'] == 'Bank only'], index='dominantSector', values='valueEUR',
                            aggfunc='mean')

        norddflong = lenderdf[(lenderdf['Deal Category'] == 'Bank only') & (lenderdf['name'].str.contains('Norddeutsche'))]
        norddf = pd.pivot_table(norddflong, index='dominantSector', values='valueEUR', aggfunc='mean')

        df = df.merge(norddf,left_index=True,right_index=True)
        df.columns=['Market average ticket','Nord/LB average ticket']

        fig = px.bar(df,barmode='group')
        fig.update_layout(xaxis={'categoryorder':'total descending'})
        st.write(fig)

        with st.expander('See data'):
            norddflong


    col1,col2 = st.columns(2)

    with col1:

        st.subheader('Total invested on insto only deals')

        df = pd.pivot_table(lenderdf[lenderdf['Deal Category'] == 'Insto only'], index='dominantSector', columns='Categories',values='valueEUR',aggfunc='sum')
        fig = px.bar(df)
        fig.update_layout(xaxis={'categoryorder':'total descending'})
        st.write(fig)

    with col2:

        st.subheader('Average ticket size on insto only deals')

        df = pd.pivot_table(lenderdf[lenderdf['Deal Category'] == 'Insto only'], index='dominantSector', values='valueEUR',
                            aggfunc='mean')

        fig = px.bar(df)
        fig.update_layout(xaxis={'categoryorder':'total descending'})
        st.write(fig)


    col1,col2 = st.columns(2)

    with col1:

        st.subheader('Total invested on mixed deals')

        df = pd.pivot_table(lenderdf[lenderdf['Deal Category'] == 'Mixed'], index='dominantSector', columns='Categories',values='valueEUR',aggfunc='sum')
        fig = px.bar(df)
        fig.update_layout(xaxis={'categoryorder':'total descending'})
        st.write(fig)

    with col2:

        st.subheader('Average ticket size on mixed deals')

        df = pd.pivot_table(lenderdf[lenderdf['Deal Category'] == 'Mixed'], index='dominantSector',values='valueEUR',
                            aggfunc='mean')


        norddflong = lenderdf[(lenderdf['Deal Category'] == 'Mixed') & (lenderdf['name'].str.contains('Norddeutsche'))]
        norddf = pd.pivot_table(norddflong, index='dominantSector', values='valueEUR',aggfunc='mean')

        df = df.merge(norddf,left_index=True,right_index=True)
        df.columns=['Market average ticket','Nord/LB average ticket']


        fig = px.bar(df,barmode='group')
        fig.update_layout(xaxis={'categoryorder':'total descending'})
        st.write(fig)

    st.subheader('Average ticket size on mixed deals - split by lender type')

    df = pd.pivot_table(lenderdf[lenderdf['Deal Category'] == 'Mixed'], index=['dominantSector'],columns='Categories',values='valueEUR', aggfunc='mean')

    fig = px.bar(df,barmode='group')
    st.write(fig)

    with st.expander('See data'):
        norddflong
        df


with tab3:


    fig = px.treemap(lenderdf[lenderdf['valueEUR'] > 0], path=['Deal Category','Bank / Insto', 'dominantSector', 'Categories','name', 'Deal name'],
                     values='valueEUR', color='name')
    st.write(fig)

    fig = px.treemap(lenderdf[lenderdf['valueEUR'] > 0], path=['Deal Category', 'Bank / Insto','Categories','name', 'dominantSector', 'Deal name'],
                     values='valueEUR', color='name')
    st.write(fig)

    fig = px.treemap(lenderdf[lenderdf['valueEUR'] > 0],
                     path=['dominantSector', 'Deal Category','Categories', 'name', 'Deal name'],
                     values='valueEUR', color='name')
    st.write(fig)

    st.header('Banks that have the highest proportion of mixed deals')

    st.caption('Min 10 deals in the sector')

    mixeddf = pd.pivot_table(lenderdf[(lenderdf['Bank / Insto']=='Bank')&(lenderdf['Deal Category']=='Mixed')],index=['name'],columns='dominantSector',values='valueEUR',aggfunc='count')
    df = pd.pivot_table(lenderdf[lenderdf['Bank / Insto'] == 'Bank'],
                        index=['name'], columns='dominantSector', values='valueEUR', aggfunc='count')


#min 10 deals per bank

    df = df[(df>10)]

    df = mixeddf.div(df)
    df.dropna(how='all', inplace=True)
    st.write(df.style.format('{:.2%}'))

    st.header('Which banks with which investors?')
    st.caption('Min 2 deals together')
    st.caption('Government entities are excluded')

    st.subheader('Renewables')

    mixdealbanks = lenderdf[(lenderdf['Deal Category']=='Mixed')&(lenderdf['Bank / Insto']=='Bank')&(lenderdf['Categories']!='Government Entity')&(lenderdf['dominantSector']=='Renewables')]
    mixdealinstos = lenderdf[(lenderdf['Deal Category']=='Mixed')&(lenderdf['Bank / Insto']=='Insto')&(lenderdf['Categories']!='Government Entity')&(lenderdf['dominantSector']=='Renewables')]

    mixdealbanks['Banks'] = mixdealbanks['name']
    mixdealinstos['Instos'] = mixdealbanks['name']

    bigdf = mixdealbanks.merge(mixdealinstos,left_on='Deal name',right_on='Deal name')

    df = pd.pivot_table(bigdf,values='valueEUR_x',index ='Name_x' ,columns='Name_y',aggfunc='count')
    df = df[df>1]
    df.dropna(how='all',inplace=True)
    df.dropna(how='all', axis=1,inplace=True)
    df

    st.subheader('Telecommunications')

    mixdealbanks = lenderdf[(lenderdf['Deal Category']=='Mixed')&(lenderdf['Bank / Insto']=='Bank')&(lenderdf['Categories']!='Government Entity')&(lenderdf['dominantSector']=='Telecommunications')]
    mixdealinstos = lenderdf[(lenderdf['Deal Category']=='Mixed')&(lenderdf['Bank / Insto']=='Insto')&(lenderdf['Categories']!='Government Entity')&(lenderdf['dominantSector']=='Telecommunications')]

    mixdealbanks['Banks'] = mixdealbanks['name']
    mixdealinstos['Instos'] = mixdealbanks['name']

    bigdf = mixdealbanks.merge(mixdealinstos,left_on='Deal name',right_on='Deal name')

    df = pd.pivot_table(bigdf,values='valueEUR_x',index ='Name_x' ,columns='Name_y',aggfunc='count')
    df = df[df>1]
    df.dropna(how='all',inplace=True)
    df.dropna(how='all', axis=1,inplace=True)
    df

    st.header('List deals by investor')

    instoselect = st.selectbox('Pick an investor',instolist)

    lenderdf[(lenderdf['name'].str.contains(instoselect)) & (lenderdf['name'] != 'N/A')&(lenderdf['valueEUR'] > 0)]

    # Average ticket size by insto vs ticket size per deal?

    instolenderdf = lenderdf[(lenderdf['Bank / Insto']=='Insto')&(lenderdf['valueEUR']>0)]

    includesector = st.selectbox('Select data',['Investors only','Include sector'])

    if includesector == 'Investors only':
        df = pd.pivot_table(instolenderdf,values='valueEUR',index='name',aggfunc=['count','sum','mean','median'])
    else:
        df = pd.pivot_table(instolenderdf, values='valueEUR', index=['name', 'dominantSector'],
                            aggfunc=['count', 'sum', 'mean', 'median'])

    # df.to_excel('ticketsizes.xlsx')

    st.write(df.style.format('{:,.2f}'))

    st.header('Deals where instos invest')

    df = pd.pivot_table(instolenderdf,values='summary.debtsizeEUR',index=['dominantSector'],aggfunc=['count','mean','median'])
    df