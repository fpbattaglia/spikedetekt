from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from pylab import *
import wx
from spikedetekt.plotting import SpikeTable
import parser

help_text = '''
Spike viewer for SpikeDetekt

Open HDF5 file (.h5 format) generated by cluster_from_raw_data.py

Choose spike number to view, spikes are shown in the bottom panel. Masked
channels are shown grey and unmasked in colour. Select whether to show
filtered or unfiltered data.

Reduce the spike list by giving a Python condition, e.g. sum(channel_mask)>5,
available variables are:
- time (int)
- channel_mask (bool array length num_channels)
- wave (float array size num_samples x num_channels)
- unfiltered_wave (int array size num_samples x num_channels)
- fet (float array size num_channels x features_per_channel)
- fet_mask (bool array length features_per_channel*num_channels+1)
'''

class SpikeViewerFrame(wx.Frame):
    def __init__(self, parent, title):

        self.filename = self.spiketable = self.indices = None
        
        wx.Frame.__init__(self, parent, title=title, size=(800, 600))
        
        ####################### MENU #######################################
        self.toolbar = self.CreateToolBar(wx.TB_TEXT|wx.TB_FLAT)
        toolquit = self.toolbar.AddLabelTool(wx.ID_EXIT, 'Quit',
                                     wx.ArtProvider.GetBitmap(wx.ART_QUIT))
        toolopen = self.toolbar.AddLabelTool(wx.ID_OPEN, 'Open',
                                     wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN))
        toolproperties = self.toolbar.AddLabelTool(wx.ID_PROPERTIES, 'Properties',
                                 wx.ArtProvider.GetBitmap(wx.ART_INFORMATION))
        toolhelp = self.toolbar.AddLabelTool(wx.ID_HELP, 'Help',
                                 wx.ArtProvider.GetBitmap(wx.ART_HELP))
        self.toolbar.Realize()
        
        self.statusbar = self.CreateStatusBar()
                        
        ####################### MAIN FRAME ##################################
        vgrid = wx.FlexGridSizer(2, 1, 0 ,0)
        self.controlpanel = wx.Panel(self, style=wx.NO_BORDER)
        self.spikedisplay = SpikeDisplayPanel(self)
        vgrid.Add(self.controlpanel, 1, wx.EXPAND)
        vgrid.Add(self.spikedisplay, 1, wx.EXPAND)
        vgrid.AddGrowableRow(1, 1)
        vgrid.AddGrowableCol(0, 1)
        self.SetSizer(vgrid)

        ####################### CONTROL PANEL ##################################
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.controlpanel_grid = wx.FlexGridSizer(rows=2, cols=2,
                                                  vgap=5, hgap=5)
        hbox.Add(self.controlpanel_grid, proportion=1,
                 flag=wx.ALL|wx.EXPAND, border=5)
        self.controlpanel.SetSizer(hbox)
        # spike number control and filtering option
        spikenum = wx.StaticText(self.controlpanel, label="Spike number")
        self.spinctl = wx.SpinCtrl(self.controlpanel, min=0,
                                   max=0,
                                   initial=0)
        self.samplefiltering = wx.CheckBox(self.controlpanel, label="Filtering",
                                           style=wx.ALIGN_RIGHT)
        self.samplefiltering.SetValue(True)
        spikegrid = wx.FlexGridSizer(rows=1, cols=2, vgap=0, hgap=10)
        spikegrid.AddMany([(self.spinctl, 1, wx.EXPAND),
                           self.samplefiltering])
        spikegrid.AddGrowableCol(0, 1)
        # filter control
        text_filter = wx.StaticText(self.controlpanel, label="Condition")
        self.filter = wx.TextCtrl(self.controlpanel)
        self.dofilter = wx.Button(self.controlpanel, label="Apply")
        filtergrid = wx.FlexGridSizer(rows=1, cols=2, vgap=0, hgap=0)
        filtergrid.AddMany([(self.filter, 1, wx.EXPAND), self.dofilter])
        filtergrid.AddGrowableCol(0)
        # add to grid
        self.controlpanel_grid.AddMany([
            #spikenum,           (self.spinctl, 1, wx.EXPAND),
            spikenum,           (spikegrid, 1, wx.EXPAND),
            text_filter,        (filtergrid, 1, wx.EXPAND),
            ])
        self.controlpanel_grid.AddGrowableCol(1, 1)

        ####################### EVENTS ##################################
        self.spinctl.Bind(wx.EVT_SPINCTRL, self.change_spike_number)
        self.samplefiltering.Bind(wx.EVT_CHECKBOX, self.change_spike_number)
        self.dofilter.Bind(wx.EVT_BUTTON, self.apply_filter)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_TOOL, self.OnQuit, toolquit)
        self.Bind(wx.EVT_TOOL, self.OnOpen, toolopen)
        self.Bind(wx.EVT_TOOL, self.OnProperties, toolproperties)
        self.Bind(wx.EVT_TOOL, self.OnHelp, toolhelp)
        
        ####################### INITIALISE DISPLAY #############################
        self.spikedisplay.draw()
        self.Centre()
        
    def change_spike_number(self, evt):
        self.spikedisplay.spike = self.spiketable[self.indices[self.spinctl.GetValue()]]
        self.spikedisplay.filtering = self.samplefiltering.GetValue()
        self.spikedisplay.draw()
        
    def changed_indices(self):
        if self.filename is not None:
            self.spinctl.SetValue(0)
            self.spinctl.SetRange(0, len(self.indices)-1)
            self.spikedisplay.spike = self.spiketable[0]
            self.statusbar.SetStatusText('Total spikes: '+str(len(self.indices)))
        else:
            self.statusbar.SetStatusText('')
    
    def apply_filter(self, evt):
        self.indices = []
        filter = self.filter.GetValue()
        if not filter.strip():
            return
        try:
            for i, spike in enumerate(self.spiketable):
                names = parser.suite(filter).compile().co_names
                d = {}
                for name in names:
                    try:
                        d[name] = getattr(spike, name)
                    except IndexError:
                        d[name] = globals()[name]                
                if eval(filter, d):
                    self.indices.append(i)
        except Exception, ex:
            dial = wx.MessageDialog(None, 'Bad filter, error:\n\n'+repr(ex),
                                    'Bad filter', wx.OK)
            dial.ShowModal()
            return
        self.changed_indices()
        self.change_spike_number(None)

    def OnOpen(self, e):
        dial = wx.FileDialog(None, "Choose an HDF5 spike table file",
                             wildcard='*.h5')
        dial.ShowModal()
        self.load(dial.GetPath())
    
    def load(self, filename):
        if self.spiketable is not None:
            self.spiketable.close()
        self.filename = filename
        self.spiketable = SpikeTable(filename)
        self.indices = arange(self.spiketable.numspikes)
        self.changed_indices()
        self.spikedisplay.draw()
    
    def OnProperties(self, e):
        if self.spiketable is not None:
            st = self.spiketable
            props = '\n'.join([
                'Filename: '+st.filename,
                'Num spikes: %d'%st.numspikes,
                'Num channels: %d'%st.numchannels,
                'Features per channel: %d'%st.features_per_channel,
                'Num features: %d'%st.numfeatures,
                'Samples per spike: %d'%st.samples_per_spike
                ])
            dial = wx.MessageDialog(None, props,
                                    'Spike table properties', wx.OK)
            dial.ShowModal()
    
    def OnHelp(self, e):
        dial = wx.MessageDialog(None, help_text, 'Help for SpikeViewer', wx.OK)
        dial.ShowModal()
    
    def OnQuit(self, e):
        self.Close()
    
    def OnClose(self, e):
        self.Close()    
    
    def Close(self):
        if self.spiketable is not None:
            self.spiketable.close()
        self.Destroy()
            
class SpikeDisplayPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1, size=(50,50), style=wx.NO_BORDER)
        self.spike = None
        self.filtering = True
        self.parent = parent
        self.figure = Figure()
        self.axes = self.figure.add_subplot(111)
        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self.axes.set_axis_bgcolor('black')
        self.canvas = FigureCanvas(self, -1, self.figure)
        self._SetSize()
        self._resizeflag = False
        self.Bind(wx.EVT_IDLE, self._onIdle)
        self.Bind(wx.EVT_SIZE, self._onSize)
    def _onSize( self, event ):
        self._resizeflag = True
    def _onIdle( self, evt ):
        if self._resizeflag:
            self._resizeflag = False
            self._SetSize()
    def _SetSize( self ):
        pixels = tuple( self.GetClientSize() )
        self.SetSize( pixels )
        self.canvas.SetSize( pixels )
        self.figure.set_size_inches( float( pixels[0] )/self.figure.get_dpi(),
                                     float( pixels[1] )/self.figure.get_dpi() )
    def draw(self):
        spike = self.spike
        if spike is not None:
            ax = self.axes = self.figure.add_subplot(111)
            ax.cla()
            if self.filtering:
                W = spike.wave
            else:
                W = spike.unfiltered_wave
            ax.plot(W, c=(0.2,)*3)
            ax.plot(W[:, spike.channel_mask.nonzero()[0]])
            ax.axvline(W.shape[0]/2, ls='--', c='w')
            ax.axis('tight')
            ax.set_xticks([])
            ax.set_yticks([])
            self.canvas.draw()
    
app = wx.App(redirect=False)
frame = SpikeViewerFrame(None, "Spike viewer")
frame.Show()
app.MainLoop()