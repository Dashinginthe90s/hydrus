import os
import typing

from hydrus.core import HydrusData
from hydrus.core import HydrusPaths
from hydrus.core import HydrusExceptions

def CheckFullPrefixCoverage( merge_target, prefixes ):
    
    missing_prefixes = GetMissingPrefixes( merge_target, prefixes )
    
    if len( missing_prefixes ) > 0:
        
        list_of_problems = ', '.join( missing_prefixes )
        
        raise HydrusExceptions.DataMissing( 'Missing storage spaces! They are, or are sub-divisions of:' + list_of_problems )
        
    

def GetMissingPrefixes( merge_target: str, prefixes: typing.Collection[ str ], min_prefix_length_allowed = 3, prefixes_are_filtered: bool = False ):
    
    # given a merge target of 'tf'
    # do these prefixes, let's say { tf0, tf1, tf2, tf3, tf4, tf5, tf6, tf7, tf8, tf9, tfa, tfb, tfc, tfd, tfe, tff }, add up to 'tf'?
    
    hex_chars = '0123456789abcdef'
    
    if prefixes_are_filtered:
        
        matching_prefixes = prefixes
        
    else:
        
        matching_prefixes = { prefix for prefix in prefixes if prefix.startswith( merge_target ) }
        
    
    missing_prefixes = []
    
    for char in hex_chars:
        
        expected_prefix = merge_target + char
        
        if expected_prefix in matching_prefixes:
            
            # we are good
            pass
            
        else:
            
            matching_prefixes_for_this_char = { prefix for prefix in prefixes if prefix.startswith( expected_prefix ) }
            
            if len( matching_prefixes_for_this_char ) > 0 or len( expected_prefix ) < min_prefix_length_allowed:
                
                missing_for_this_char = GetMissingPrefixes( expected_prefix, matching_prefixes_for_this_char, prefixes_are_filtered = True )
                
                missing_prefixes.extend( missing_for_this_char )
                
            else:
                
                missing_prefixes.append( expected_prefix )
                
            
        
    
    return missing_prefixes
    

class FilesStorageBaseLocation( object ):
    
    def __init__( self, path: str, ideal_weight: int, max_num_bytes = None ):
        
        if not os.path.isabs( path ):
            
            path = HydrusPaths.ConvertPortablePathToAbsPath( path )
            
        
        self.path = path
        self.ideal_weight = ideal_weight
        self.max_num_bytes = max_num_bytes
        
    
    def __eq__( self, other ):
        
        if isinstance( other, FilesStorageBaseLocation ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return self.path.__hash__()
        
    
    def __repr__( self ):
        
        return f'{self.path} ({self.ideal_weight}, {self.max_num_bytes})'
        
    
    def AbleToAcceptSubfolders( self, current_num_bytes: int, num_bytes_of_subfolder: int ):
        
        if self.max_num_bytes is not None:
            
            if current_num_bytes + num_bytes_of_subfolder > self.max_num_bytes:
                
                return False
                
            
        
        if self.ideal_weight == 0:
            
            return False
            
        
        return True
        
    
    def EagerToAcceptSubfolders( self, current_normalised_weight: float, total_ideal_weight: int, weight_of_subfolder: float, current_num_bytes: int, num_bytes_of_subfolder: int ):
        
        if self.max_num_bytes is not None:
            
            if current_num_bytes + num_bytes_of_subfolder > self.max_num_bytes:
                
                return False
                
            
        
        if self.ideal_weight == 0:
            
            return False
            
        
        ideal_normalised_weight = self.ideal_weight / total_ideal_weight
        
        if current_normalised_weight + weight_of_subfolder > ideal_normalised_weight:
            
            return False
            
        
        return True
        
    
    def GetPortablePath( self ):
        
        return HydrusPaths.ConvertAbsPathToPortablePath( self.path )
        
    
    def HasNoUpperLimit( self ):
        
        return self.max_num_bytes is None
        
    
    def MakeSureExists( self ):
        
        HydrusPaths.MakeSureDirectoryExists( self.path )
        
    
    def NeedsToRemoveSubfolders( self, current_num_bytes: int ):
        
        if self.max_num_bytes is not None and current_num_bytes > self.max_num_bytes:
            
            return True
            
        
        return False
        
    
    def PathExists( self ):
        
        return os.path.exists( self.path ) and os.path.isdir( self.path )
        
    
    def WouldLikeToRemoveSubfolders( self, current_normalised_weight: float, total_ideal_weight: int, weight_of_subfolder: float ):
        
        if self.ideal_weight == 0:
            
            return True
            
        
        ideal_normalised_weight = self.ideal_weight / total_ideal_weight
        
        # the weight_of_subfolder here is a bit of padding to make sure things stay a bit more bistable
        return current_normalised_weight - weight_of_subfolder > ideal_normalised_weight
        
    

class FilesStorageSubfolder( object ):
    
    def __init__( self, prefix: str, base_location: FilesStorageBaseLocation, purge: bool = False ):
        
        self.prefix = prefix
        self.base_location = base_location
        self.purge = purge
        
        #
        
        first_char = self.prefix[0]
        hex_chars = self.prefix[1:]
        
        # convert 'b' to ['b'], 'ba' to ['ba'], 'bad' to ['ba', 'd'], and so on  
        our_subfolders = [ hex_chars[ i : i + 2 ] for i in range( 0, len( hex_chars ), 2 ) ]
        
        # restore the f/t char
        our_subfolders[0] = first_char + our_subfolders[0]
        
        self.path = os.path.join( self.base_location.path, *our_subfolders )
        
    
    def __repr__( self ):
        
        if self.prefix[0] == 'f':
            
            t = 'file'
            
        elif self.prefix[0] == 't':
            
            t = 'thumbnail'
            
        else:
            
            t = 'unknown'
            
        
        return f'{t} {self.prefix[1:]} at {self.path}'
        
    
    def GetNormalisedWeight( self ):
        
        num_hex = len( self.prefix ) - 1
        
        return 1 / ( 16 ** num_hex )
        
    
    def GetFilePath( self, filename: str ) -> str:
        
        return os.path.join( self.path, filename )
        
    
    def IsForFiles( self ):
        
        return self.prefix[0] == 'f'
        
    
    def MakeSureExists( self ):
        
        HydrusPaths.MakeSureDirectoryExists( self.path )
        
    
    def PathExists( self ):
        
        return os.path.exists( self.path ) and os.path.isdir( self.path )
        
    
