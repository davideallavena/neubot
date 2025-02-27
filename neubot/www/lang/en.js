// neubot/www/lang/en.js

//
// Copyright (c) 2011 Simone Basso <bassosimone@gmail.com>,
//  NEXA Center for Internet & Society at Politecnico di Torino
//
// This file is part of Neubot <http://www.neubot.org/>.
//
// Neubot is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Neubot is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Neubot.  If not, see <http://www.gnu.org/licenses/>.
//

//
// WARNING! Autogenerated file: don't edit
// Use './scripts/make_lang_en.py' instead to regenerate it
// Created: Fri, 20 Jan 2012 16:14:34 GMT
//

var LANG = {
    'Current test results': 'Current test results',

    'Disable': 'Disable',

    'Enable': 'Enable',

    'Latest test results': 'Latest test results',

    'Test running': 'Test running',

    'Your bittorrent download and upload speed': 'Your bittorrent download and upload speed',

    'Your download and upload speed': 'Your download and upload speed',

    'disabled': 'disabled',

    'enabled': 'enabled',

    'i18n_about': 'About',

    'i18n_about_text':
'This is the web user interface of Neubot v0.4.6-rc3.\
 Neubot is a lightweight <a href="http://www.neubot.org/copying">open-source</a> program\
 that runs in background and periodically performs\
 transmission tests to probe your Internet connection\
 using various application level protocols. <a href="http://www.neubot.org/faq">Read more</a>',

    'i18n_bittorrent': 'Bittorrent',

    'i18n_bittorrent_explanation':
'This tests downloads and uploads a given number of bytes from\
 a remote server using the BitTorrent protocol. It reports the\
 average download and upload speed measured during the test as\
 well as the time required to connect to the remote server,\
 which approximates the round-trip time latency.',

    'i18n_bittorrent_explanation_2':
'Please, note that this test is quite different from the speedtest\
 one, so there are cases where the comparison between the two is not\
 feasible. We\'re working to deploy an HTTP test that mimics the\
 behavior of this one, so that it\'s always possible to compare them.',

    'i18n_bittorrent_see_last': 'View last',

    'i18n_bittorrent_see_last_days': 'day',

    'i18n_bittorrent_see_last_hours': 'hour',

    'i18n_bittorrent_title': 'Your recent bittorrent results',

    'i18n_collect_status_text':
'The daemon is uploading the results of the latest\
 transmission test to the neubot project servers.',

    'i18n_current_status': 'Current Neubot status',

    'i18n_description': 'Description',

    'i18n_dlspeed': 'Download speed',

    'i18n_footer_text':
'Neubot is a research project on network neutrality of the<br/>\
 <a href="http://nexa.polito.it/">NEXA Center for Internet &amp;\
 Society</a> at <a href="http://www.dauin.polito.it/">Politecnico\
 di Torino</a>.',

    'i18n_header_subtitle': 'The web-interface to control the neubot daemon',

    'i18n_header_title': '<a href="index.html">Neubot web interface</a>',

    'i18n_idle_status_text':
'The daemon is sleeping. The next rendezvous will\
 start in <em><span id="next_rendezvous">(information\
 not available)</span></em>.',

    'i18n_infonav': '(n/a)',

    'i18n_latency': 'Latency',

    'i18n_latest': 'Latest test details',

    'i18n_log': 'Log',

    'i18n_negotiate_status_text':
'The daemon is waiting for its turn to perform a\
 transmission test. The last known position in queue\
 is <em><span id="queuePos">(no negotiations\
 yet)</span></em>.',

    'i18n_neubotis': 'Neubot is',

    'i18n_privacy': 'Privacy',

    'i18n_privacy_explanation':
'In this page we spell out the details of our <a href="#policy">privacy policy</a>, in order to comply with\
 European law. And we provide a simple <a href="#dashboard">privacy\
 dashboard</a> to manage the permissions you give us with\
 respect to the treatment of your Internet address, which\
 is personal data in EU.',

    'i18n_privacy_not_ok':
'Neubot is DISABLED: starting from version 0.4.6, Neubot needs\
 all privacy permissions to be able to run tests using the\
 distributed <a href="http://www.measurementlab.net/">M-Lab</a>\
 platform. Please, provide the permissions or Neubot would not\
 work.',

    'i18n_privacy_policy':
'\r\n\
$Version: 2.0$\r\n\
\r\n\
The Neubot Project is a research effort that aims to study the quality\r\n\
and neutrality of ordinary users\' Internet connections, to rebalance the\r\n\
information asymmetry between them and Service Providers.  The Neubot\r\n\
Software (i) *measures* the quality and neutrality of your Internet\r\n\
connection.  The raw measurement results are (ii) *collected* on the\r\n\
measurement servers for research purposes and (iii) *published*, to allow\r\n\
other individuals and institutions to reuse them for research purposes.\r\n\
\r\n\
To *measure* the quality and neutrality of your Internet connection,\r\n\
the Neubot Software does not monitor or analyze your Internet traffic.\r\n\
It just uses a fraction of your connection capacity to perform background\r\n\
transmission tests, sending and/or receiving random data.  The results\r\n\
contain the measured performance metrics, such as the download speed,\r\n\
or the latency, as well as your computer load, as a percentage, and\r\n\
*your Internet address*.\r\n\
\r\n\
The Internet address is paramount because it allows to *infer your Internet\r\n\
Service Provider* and to have a rough idea of *your location*, allowing to\r\n\
put the results in context.  The Neubot Project needs to *collect* it\r\n\
to study the data and wants to *publish* it to enable other individuals\r\n\
and institutions to carry alternative studies and/or peer-review its\r\n\
measurement and data analysis methodology.  This is coherent with the\r\n\
policy of the distributed server platform that empowers the Neubot\r\n\
Project, Measurement Lab (M-Lab), which requires all results to be\r\n\
released as open data [1].\r\n\
\r\n\
You are reading this privacy policy because Neubot is developed in the\r\n\
European Union, where there is consensus that Internet addresses are\r\n\
*personal data*.  This means that the Neubot Project cannot store, process\r\n\
or publish your address without your prior *informed consent*, under the\r\n\
provisions of the &quot;Codice in materia di protezione dei dati personali&quot;\r\n\
(Decree 196/03) [2].  In accordance with the law, data controller is the\r\n\
NEXA Center for Internet &amp; Society [3], represented by its co-director Juan\r\n\
Carlos De Martin.\r\n\
\r\n\
Via its web interface [4], the Neubot software asks you (a) to explicitly\r\n\
assert that you are *informed*, i.e. that you have read the privacy\r\n\
policy, (b) to give it the permission to *collect* and (c) *publish* your\r\n\
IP address.  If you don\'t assert (a) and you don\'t give the permission\r\n\
to do (b) and (c), Neubot cannot run tests because, if it did, it would\r\n\
violate privacy laws and/or Measurement Lab policy.\r\n\
\r\n\
The data controller guarantees you the rights as per Art. 7 of the\r\n\
above-mentioned Decree 196/03.  Basically, you have total control over\r\n\
you personal data, and you can, for example, inquire Neubot to remove\r\n\
your Internet address from its data sets.  To exercise your rights, please\r\n\
write to &lt;privacy@neubot.org&gt; or to &quot;NEXA Center for Internet\r\n\
&amp; Society, Dipartimento di Automatica e Infomatica, Politecnico di\r\n\
Torino, Corso Duca degli Abruzzi 24, 10129 Turin, ITALY.&quot;\r\n\
\r\n\
[1] http://www.measurement-lab.net/about\r\n\
[2] http://www.garanteprivacy.it/garante/doc.jsp?ID=1311248\r\n\
[3] http://nexa.polito.it/\r\n\
[4] http://127.0.0.1:9774/privacy.html\r\n\
        ',

    'i18n_privacy_settings_1': 'This is the current state of your privacy settings:',

    'i18n_privacy_settings_2_can_collect':
'<b>Can collect</b> You give Neubot\
 the permission to collect your Internet address for research\
 purposes',

    'i18n_privacy_settings_2_can_publish':
'<b>Can publish</b> You give Neubot the\
 permission to publish your Internet address on the Web, so that\
 it can be reused for research purposes',

    'i18n_privacy_settings_2_informed':
'<b>Informed</b> You assert that you\
 have read and understood the above privacy policy',

    'i18n_privacy_title_1': 'Privacy policy',

    'i18n_privacy_title_2': 'Privacy dashboard',

    'i18n_privacy_warning':
'<b>WARNING! Neubot does not run any test unless you assert that\
 you have read the privacy policy and you provide the permission\
 to collect and publish your Internet address.</b>',

    'i18n_rendezvous_status_text':
'The daemon is connecting to the <em>master server</em>\
 and retrieves test instructions and update information.',

    'i18n_resultof': 'Result of',

    'i18n_settings': 'Settings',

    'i18n_settings_par1':
'In this page we list all the knobs you can twist,\
 including obscure and dangerous settings.\
 Please, make sure you understand what you are doing\
 before making any change. You\'re on your own if\
 something breaks because of your changes.',

    'i18n_settings_par2':
'Some settings, such as <code>agent.api.address</code>\
 and <code>agent.api.port</code>, are not effective\
 until you restart Neubot.',

    'i18n_settings_title': 'Settings',

    'i18n_speedtest': 'Speedtest',

    'i18n_speedtest_explanation_1':
'Speedtest is a test that sheds some light on the quality\
 of your broadband connection, by downloading/uploading random data\
 to/from a remote server, and reporting the average speeds. The\
 test also yields an over-estimate of the round-trip latency between\
 you and such remote server. For more information, see the\
<a href="http://www.neubot.org/faq#what-does-speedtest-test-measures">FAQ</a>.',

    'i18n_speedtest_explanation_2':
'To put the results of this test in the context of the\
 average broadband speed available in your country you\
 might want to check the statistics available at the <a href="http://www.oecd.org/sti/ict/broadband">OECD Broadband\
 Portal</a>. In particular, it might be interesting to read <a href="http://www.oecd.org/dataoecd/10/53/39575086.xls">&quot;Average\
 advertised download speeds, by country&quot;</a> (in XLS format).',

    'i18n_speedtest_see_last': 'View last',

    'i18n_speedtest_see_last_days': 'day',

    'i18n_speedtest_see_last_hours': 'hour',

    'i18n_speedtest_title': 'Your recent speedtest results',

    'i18n_startnow': 'Manually start test',

    'i18n_startnowtest': 'Test',

    'i18n_state': 'State',

    'i18n_status': 'Status',

    'i18n_status_text':
'This is the web interface to control the <em>neubot daemon</em>,\
 that is running in background with pid <em>\
 <span id="pid">(information not available)</span></em> since\
 <em><span id="since">(information not available)</span></em>.\
 The following table provides some more details on the state of\
 the daemon and highlights the current state.',

    'i18n_test_status_text':
'The daemon is performing a transmission test. The\
 name of the test is <em><span id="testName">\
 (no tests yet)</span></em>.',

    'i18n_ulspeed': 'Upload speed',

    'i18n_update_available':
'Please, note that an updated version of Neubot is available at\
 <a href="http://www.neubot.org/download">Neubot.org</a>.',

    'i18n_update_title': 'A new version is available',

    'i18n_updavailable': 'Updates available',

    'i18n_website': 'Neubot web site',

    'i18n_welcome_text':
'Thank you for using Neubot! You are gaining some understanding\
 about your Internet Connection and helping the Internet Community\
 to understand what is going on in the network. This tab provides\
 a general overview of the status of the neubot daemon. Above there\
 are a number of tabs, one for each available transmission test.\
 Each tab provides more information on the test and allows you to\
 review your recent results.'

};
